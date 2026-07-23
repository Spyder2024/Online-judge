import json
from typing import List, Dict, Any, Optional
from app.core.redis import get_redis

class RedisLeaderboardService:
    """
    High-concurrency Redis Leaderboard Engine backed by Redis Sorted Sets (ZSET).
    Key format: contest:{contest_id}:leaderboard
    Score calculation formula: score * 10^8 - penalty_seconds
    This guarantees higher scores rank higher, and tied scores rank by lowest penalty time.
    """
    
    @staticmethod
    def _get_key(contest_id: int) -> str:
        return f"contest:{contest_id}:leaderboard"
        
    @staticmethod
    def _get_user_meta_key(contest_id: int) -> str:
        return f"contest:{contest_id}:user_meta"

    @classmethod
    async def update_score(
        cls,
        contest_id: int,
        user_id: int,
        username: str,
        score_delta: float,
        penalty_delta_seconds: int
    ) -> float:
        """
        Atomically update a contestant's score and penalty time using Redis Pipeline.
        """
        client = await get_redis()
        meta_key = cls._get_user_meta_key(contest_id)
        
        # Get existing meta or default
        user_meta_str = await client.hget(meta_key, str(user_id))
        if user_meta_str:
            meta = json.loads(user_meta_str)
        else:
            meta = {"username": username, "score": 0.0, "penalty": 0}
            
        meta["score"] += score_delta
        meta["penalty"] += penalty_delta_seconds
        meta["username"] = username
        
        # Calculate composite score for ZSET sorting
        # 100000000 - penalty ensures smaller penalty yields higher composite ranking
        composite_score = (meta["score"] * 100000000) - meta["penalty"]
        
        pipe = client.pipeline()
        pipe.hset(meta_key, str(user_id), json.dumps(meta))
        pipe.zadd(cls._get_key(contest_id), {str(user_id): composite_score})
        await pipe.execute()
        
        return composite_score

    @classmethod
    async def get_leaderboard(
        cls,
        contest_id: int,
        offset: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Fetch top performers instantly from Redis ZSET using ZREVRANGE without SQL table joins.
        """
        client = await get_redis()
        zset_key = cls._get_key(contest_id)
        meta_key = cls._get_user_meta_key(contest_id)
        
        # Fetch ordered user_ids from ZSET
        rankings = await client.zrevrange(zset_key, offset, offset + limit - 1, withscores=True)
        if not rankings:
            return []
            
        user_ids = [u_id for u_id, _ in rankings]
        user_metas_raw = await client.hmget(meta_key, user_ids)
        
        leaderboard = []
        for rank_idx, (user_id, comp_score) in enumerate(rankings, start=offset + 1):
            raw_meta = user_metas_raw[user_ids.index(user_id)]
            if raw_meta:
                meta = json.loads(raw_meta)
            else:
                meta = {"username": f"User_{user_id}", "score": 0.0, "penalty": 0}
                
            leaderboard.append({
                "rank": rank_idx,
                "user_id": int(user_id),
                "username": meta["username"],
                "score": meta["score"],
                "penalty_seconds": meta["penalty"],
                "composite_score": comp_score
            })
            
        return leaderboard
