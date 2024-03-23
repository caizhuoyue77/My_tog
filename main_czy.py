from tqdm import tqdm
import argparse
import random
from czy_func import * # 导入与Wikipedia/Wikidata相关的函数
from client import * # 导入API交互的客户端函数
from czy_client import *
from utils import *
from log import *

if __name__ == '__main__':
    # 这些先不要改动
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str,
                        default="webqsp", help="choose the dataset.")
    parser.add_argument("--max_length", type=int,
                        default=256, help="the max length of LLMs output.")
    parser.add_argument("--temperature_exploration", type=float,
                        default=0.4, help="the temperature in exploration stage.")
    parser.add_argument("--temperature_reasoning", type=float,
                        default=0, help="the temperature in reasoning stage.")
    parser.add_argument("--width", type=int,
                        default=3, help="choose the search width of ToG.")
    parser.add_argument("--depth", type=int,
                        default=3, help="choose the search depth of ToG.")
    parser.add_argument("--remove_unnecessary_rel", type=bool,
                        default=True, help="whether removing unnecessary relations.")
    parser.add_argument("--LLM_type", type=str,
                        default="gpt-3.5-turbo", help="base LLM model.")
    parser.add_argument("--opeani_api_keys", type=str,
                        default="", help="if the LLM_type is gpt-3.5-turbo or gpt-4, you need add your own openai api keys.")
    parser.add_argument("--num_retain_entity", type=int,
                        default=5, help="Number of entities retained during entities search.")
    parser.add_argument("--prune_tools", type=str,
                        default="llm", help="prune tools for ToG, can be llm (same as LLM_type), bm25 or sentencebert.")
    parser.add_argument("--addr_list", type=str,
                        default="server_urls.txt", help="The address of the Wikidata service.")
    args = parser.parse_args()
    
    # TODO：数据集肯定得修改
    datas, question_string = prepare_dataset(args.dataset)
    print("Start Running ToG on %s dataset." % args.dataset)
    for data in tqdm(datas):
        """
        question是需要回答的问题
        """
        question = data[question_string]

        print(f"Question: {question}")

        """
        从当前数据中拿出问题和主题实体
        """
        topic_entity = data['topic_entity']

        print(f"Topic entity: {topic_entity}")

        cluster_chain_of_entities = []

        # 处理未识别主题实体的情况
        if len(topic_entity) == 0:

            # TODO：这个函数得改

            """
            意思就是，没有关系实体的时候就直接用llm+cot来回答
            """
            results = generate_without_explored_paths(question, args)
            save_2_jsonl(question, results, [], file_name=args.dataset)
            continue

        # 关系探索的预初始化 将会存在搜索树中
        """
        初始化关系搜索
        """
        pre_relations = []
        pre_heads= [-1] * len(topic_entity)
        flag_printed = False
       
        """
        知识图谱数据库的url存下来
        """
        neo4j_config = {'uri': 'bolt://localhost:7687', 'username': 'neo4j', 'password': 'daffodil'}
        czy_client = Neo4jClient(neo4j_config)
        
        # 在推测树的不同深度上迭代
        for depth in range(1, args.depth+1):
            current_entity_relations_list = []
            i=0
            # 对最初的query里面的实体进行遍历
            for entity in topic_entity:
                if entity!="[FINISH_ID]":
                    # TODO：修改这个函数
                    retrieve_relations_with_scores = relation_search_prune(
                        entity, topic_entity[entity], pre_relations, pre_heads[i],
                          question, args, czy_client)  

                    # 把这一组实体添加到全部遍历实体中去   
                    logger.info(f"[retrieve_relations_with_scores] Entity: {entity}, Relations: {retrieve_relations_with_scores}")

                    current_entity_relations_list.extend(
                        retrieve_relations_with_scores)
                i+=1

                logger.info(f"[current_entity_relations_list] {current_entity_relations_list}")
            
            total_candidates = []
            total_scores = []
            total_relations = []
            total_entities_id = []
            total_topic_entities = []
            total_head = []

            logger.debug(current_entity_relations_list)

            # 对每个叶子结点进行扩展
            for entity in current_entity_relations_list:
                value_flag=False
                
                # 为什么要区分head，烦死了
                if 1:
                    # TODO：修改这个函数
                    # 我猜测区分头尾实体是为了后面拿出另一个实体的时候方便
                    # 防止拿出了原来那个实体

                    # logger.info(f"Entity: {entity['entity']}, Relation: {entity['relation']}")

                    node_id = entity_node_id("TopCityLookup","API", czy_client)

                    logger.info(f"Node ID: {node_id}")

                    entity_candidates_id, entity_candidates_name = entity_search(entity['entity'], entity['relation'], czy_client, True)
                else:
                    entity_candidates_id, entity_candidates_name = entity_search(entity['entity'], entity['relation'], czy_client, False)
                
                if len(entity_candidates_name)==0:
                    continue
                if len(entity_candidates_id) ==0: # values
                    value_flag=True
                    entity_candidates_id = ["[FINISH_ID]"] * len(entity_candidates_name)
                else: # ids
                    entity_candidates_id, entity_candidates_name = del_all_unknown_entity(entity_candidates_id, entity_candidates_name)
                    if len(entity_candidates_id) >=20:
                        indices = random.sample(range(len(entity_candidates_name)), 10)
                        entity_candidates_id = [entity_candidates_id[i] for i in indices]
                        entity_candidates_name = [entity_candidates_name[i] for i in indices]

                if len(entity_candidates_id) ==0:
                    continue

                # 计算这些scores是为了什么？
                # 是为了候选节点吧
                scores, entity_candidates, entity_candidates_id = entity_score(question, entity_candidates_id, entity_candidates_name, entity['score'], entity['relation'], args)
                
                # 记录当前一层所有叶子结点的下一个候选节点
                total_candidates, total_scores, total_relations, total_entities_id, total_topic_entities, total_head = update_history(entity_candidates, entity, scores, entity_candidates_id, total_candidates, total_scores, total_relations, total_entities_id, total_topic_entities, total_head, value_flag)
            
            # 无处可走了，没有可以继续搜索的节点，停止搜索
            if len(total_candidates) ==0:
                half_stop(question, cluster_chain_of_entities, depth, args)
                flag_printed = True
                break
            
            # TODO：修改这个函数
            # 从当前的候选节点中选择一组节点
            flag, chain_of_entities, entities_id, pre_relations, pre_heads = entity_prune(total_entities_id, 
                                                                                          total_relations, total_candidates, 
                                                                                          total_topic_entities, total_head, 
                                                                                          total_scores, args, wiki_client)
            cluster_chain_of_entities.append(chain_of_entities)
            if flag:
                # TODO：修改这个函数
                # reasoning：根据在kg上获得的结果获得最终答案
                # stop表示大模型有没有得到需要的内容
                stop, results = reasoning(question, cluster_chain_of_entities, args)
                if stop:
                    print("ToG stoped at depth %d." % depth)
                    save_2_jsonl(question, results, cluster_chain_of_entities, file_name=args.dataset)
                    flag_printed = True
                    break
                else:
                    print("depth %d still not find the answer." % depth)
                    flag_finish, entities_id = if_finish_list(entities_id)
                    if flag_finish:
                        half_stop(question, cluster_chain_of_entities, depth, args)
                        flag_printed = True
                    else:
                        topic_entity = {qid: topic for qid, topic in zip(entities_id, [wiki_client.query_all("qid2label", entity).pop() for entity in entities_id])}
                        continue
            else:
                half_stop(question, cluster_chain_of_entities, depth, args)
                flag_printed = True
        
        # flag_printed 是干啥的
        if not flag_printed:
            results = generate_without_explored_paths(question, args)
            save_2_jsonl(question, results, [], file_name=args.dataset)