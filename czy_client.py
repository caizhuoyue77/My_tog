from neo4j import GraphDatabase
import typing as tp
from concurrent.futures import ThreadPoolExecutor
from logger import logger

class Neo4jConnector:
    def __init__(self, uri, username, password):
        self.uri = uri
        self.username = username
        self.password = password
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def search_neighbours(self, node_id):
        query = (
            "MATCH (a)-[r]-(neighbor) "
            "WHERE ID(a) = $node_id "
            "RETURN DISTINCT neighbor, "
            "CASE WHEN (a)-[r]->(neighbor) THEN 'tail' "
            "ELSE 'head' "
            "END AS label"
        )
        with self.driver.session() as session:
            result = session.run(query, node_id=node_id)
            return [{'neighbor': record['neighbor'], 'label': record['label']} for record in result]

    def close_connection(self):
        self.driver.close()

class Neo4jClient:
    def __init__(self, neo4j_config):
        self.neo4j_connector = Neo4jConnector(**neo4j_config)
        self.executor = ThreadPoolExecutor(max_workers=4)  # 调整线程数量以适应您的需求
    
    def search_neighbours(self, node_id):
        query = (
            "MATCH (a)-[r]-(neighbor) "
            "WHERE ID(a) = $node_id "
            "RETURN DISTINCT neighbor, TYPE(r) AS relationshipType, r.label AS relationshipLabel, "  # 在这里加一个逗号
            "CASE WHEN (a)-[r]->(neighbor) THEN 'tail' "
            "ELSE 'head' "
            "END AS direction"
        )
        with self.neo4j_connector.driver.session() as session:
            result = session.run(query, node_id=node_id)
            neighbours = []
            for record in result:
                # 提取 Node 对象的属性
                node = record['neighbor']
                properties = dict(node)
                properties['id'] = node.id
                properties['relationshipType'] = record['relationshipType']
                properties['relationshipLabel'] = record['relationshipLabel']
                properties['direction'] = record['direction']
                neighbours.append(properties)
            logger.error(neighbours)
            return neighbours
       
    def find_node_id_by_name_and_type(self, node_name, node_label):
        query = (
            "MATCH (n) "
            "WHERE n.name = $node_name AND $node_label in labels(n) "
            "RETURN ID(n) AS nodeId"
        )
        with self.neo4j_connector.driver.session() as session:
            result = session.run(query, node_name=node_name, node_label=node_label)

            node_ids = [record['nodeId'] for record in result]
            return node_ids

    def search_neighbours_with_relation(self, node_id, relationship):
        query = (
            "MATCH (a)-[r]-(neighbor) "
            "WHERE ID(a) = $node_id AND TYPE(r) = $relationship "
            "RETURN DISTINCT neighbor, TYPE(r) AS relationshipType, r.label AS relationshipLabel, "
            "CASE WHEN (a)-[r]->(neighbor) THEN 'tail' "
            "ELSE 'head' "
            "END AS direction"
        )
        with self.neo4j_connector.driver.session() as session:
            result = session.run(query, node_id=node_id, relationship=relationship)
            neighbours = []
            for record in result:
                # 提取 Node 对象的属性
                node = record['neighbor']
                properties = dict(node)
                properties['id'] = node.id
                properties['relationshipType'] = record['relationshipType']
                properties['relationshipLabel'] = record['relationshipLabel']
                properties['direction'] = record['direction']
                neighbours.append(properties)
            logger.error(neighbours)
            return neighbours
    
    def separate_head_tail(self, neighbours):
        head = []
        tail = []
        for neighbour in neighbours:
            if neighbour['direction'] == 'head':
                head.append(neighbour)
            else:
                tail.append(neighbour)
        return {"head": head, "tail": tail}

    def search_neighbours_head_tail(self, node_ids):
        neighbours = self.search_neighbours(node_ids)
        head_tail_neighbours = self.separate_head_tail(neighbours)
        return head_tail_neighbours
        
    def close_all_connections(self):
        self.neo4j_connector.close_connection()