import osmnx
import geopandas
import pandas
from shapely.geometry import Point, LineString

class IdGen:
    def __init__(self, start_index=0):
        self.index = start_index
        
    def get(self, count):
        r = range(self.index, self.index + count)
        self.index += count
        return r
        
def sample_graph(g, dist, start_index=-1000000):
    id_gen = IdGen(start_index)
    
    gproj = osmnx.project_graph(g)
    nodes, edges = osmnx.graph_to_gdfs(gproj)
    
    new_node_dataframes = []
    new_edge_indices = []
    new_edge_data = []
    for row in edges.itertuples():
        orig_points = row.Index
        if orig_points[0] < orig_points[1]:
            # we assume all bidirectional, and will include both directions here 
            # to avoid creating too many points.
            continue
        
        route_number = orig_points[2]

        all_points = list(osmnx.utils_geo.interpolate_points(row.geometry, dist))
        new_point_ids = list(id_gen.get(len(all_points) - 2))
        all_point_ids = [orig_points[0]] + new_point_ids + [orig_points[1]]
    
        z = all_points[1:-1]
        if len(z):
            new_points = [Point(*q) for q in z]
            rdf = geopandas.GeoDataFrame(data={
                    'geometry': new_points, 'street_count' : 1
                }, index=new_point_ids)
            new_node_dataframes.append(rdf)
         
        # now do edges, both directions
        node_id_pairs = list(zip(all_point_ids, all_point_ids[1:]))
        node_points = zip(all_points, all_points[1:])

        for nid, node_point in zip(node_id_pairs, node_points):
            geometry = LineString(node_point)
            edge_data = row._replace(length=round(geometry.length, 2), geometry=None)
            
            new_edge_indices.append((nid[0], nid[1], route_number))
            new_edge_data.append(edge_data)
            
            new_edge_indices.append((nid[1], nid[0], route_number))
            new_edge_data.append(edge_data)
            

    new_nodes = pandas.concat([nodes] + new_node_dataframes)
    
    index = pandas.MultiIndex.from_tuples(new_edge_indices, names = ['u', 'v', 'key'])
    new_edges = geopandas.GeoDataFrame(data=new_edge_data, index=index)
    new_edges.crs = edges.crs
    
    proj_nodes = osmnx.project_gdf(new_nodes, to_latlong=True)
    proj_edges = osmnx.project_gdf(new_edges, to_latlong=True)
    
    proj_edges.drop(columns='Index', inplace=True)
    proj_nodes['x'] = proj_nodes['lon'] = proj_nodes.geometry.x
    proj_nodes['y'] = proj_nodes['lat']= proj_nodes.geometry.y
    retg = osmnx.graph_from_gdfs(proj_nodes, proj_edges)
    return retg
    