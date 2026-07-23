"""知识图谱可视化 API"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from core.auth import get_current_user
from api.deps import get_infra

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/graph/data")
async def get_graph_data(
    limit: int = Query(default=200, le=1000),
    current_user: dict = Depends(get_current_user),
    infra=Depends(get_infra),
):
    """获取图谱数据（节点+边）用于可视化"""
    graph_store = getattr(infra, 'graph_store', None)
    if not graph_store:
        raise HTTPException(503, "知识图谱未配置")

    try:
        nodes = []
        edges = []

        with graph_store._driver.session() as session:
            # 获取实体节点
            result = session.run(
                "MATCH (e:Entity) "
                "RETURN e.id AS id, e.name AS name, e.type AS type, "
                "e.description AS description, COALESCE(e.pagerank, 0.001) AS pagerank "
                "ORDER BY e.pagerank DESC LIMIT $limit",
                limit=limit,
            )
            node_ids: set[str] = set()
            for record in result:
                nid = record["id"]
                node_ids.add(nid)
                nodes.append({
                    "id": nid,
                    "name": record["name"],
                    "type": record["type"] or "unknown",
                    "description": record["description"] or "",
                    "pagerank": record["pagerank"],
                })

            # 获取关系边
            result = session.run(
                "MATCH (a:Entity)-[r:RELATES]->(b:Entity) "
                "WHERE a.id IN $ids AND b.id IN $ids "
                "RETURN a.id AS source, b.id AS target, "
                "r.description AS description, COALESCE(r.weight, 1) AS weight",
                ids=list(node_ids),
            )
            for record in result:
                edges.append({
                    "source": record["source"],
                    "target": record["target"],
                    "description": record["description"] or "",
                    "weight": record["weight"],
                })

        return {"nodes": nodes, "edges": edges}

    except Exception as e:
        logger.error("Graph data retrieval failed: %s", e)
        raise HTTPException(500, f"图谱数据获取失败: {str(e)}")


@router.get("/graph/search")
async def search_graph(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, le=100),
    current_user: dict = Depends(get_current_user),
    infra=Depends(get_infra),
):
    """搜索图谱实体"""
    graph_store = getattr(infra, 'graph_store', None)
    if not graph_store:
        raise HTTPException(503, "知识图谱未配置")

    try:
        with graph_store._driver.session() as session:
            result = session.run(
                "MATCH (e:Entity) "
                "WHERE e.name CONTAINS $q "
                "RETURN e.id AS id, e.name AS name, e.type AS type, "
                "e.description AS description, COALESCE(e.pagerank, 0.001) AS pagerank "
                "ORDER BY e.pagerank DESC LIMIT $limit",
                q=q, limit=limit,
            )
            nodes = [{
                "id": r["id"], "name": r["name"], "type": r["type"],
                "description": r["description"], "pagerank": r["pagerank"],
            } for r in result]

        return {"nodes": nodes}

    except Exception as e:
        logger.error("Graph search failed: %s", e)
        raise HTTPException(500, f"搜索失败: {str(e)}")


@router.get("/graph/stats")
async def get_graph_stats(
    current_user: dict = Depends(get_current_user),
    infra=Depends(get_infra),
):
    """获取图谱统计信息"""
    graph_store = getattr(infra, 'graph_store', None)
    if not graph_store:
        raise HTTPException(503, "知识图谱未配置")

    try:
        with graph_store._driver.session() as session:
            entity_count = session.run("MATCH (e:Entity) RETURN count(e) AS c").single()["c"]
            relation_count = session.run("MATCH ()-[r:RELATES]->() RETURN count(r) AS c").single()["c"]
            community_count = session.run("MATCH (c:Community) RETURN count(c) AS c").single()["c"]

        return {
            "entity_count": entity_count,
            "relation_count": relation_count,
            "community_count": community_count,
        }
    except Exception as e:
        logger.error("Graph stats failed: %s", e)
        raise HTTPException(500, f"统计失败: {str(e)}")
