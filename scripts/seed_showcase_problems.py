"""
scripts/seed_showcase_problems.py

Phase C: Seed top 10 canonical showcase problems into Neon PostgreSQL
with real LeetCode statements, examples, constraints, tags, and multi-case test cases.
"""

import asyncio
import os
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload

from app.models.problem import Problem, TestCase, Tag, ProblemTag, ProblemDifficulty

DEFAULT_DB_URL = "postgresql+asyncpg://neondb_owner:npg_9vnt3ybeighq@ep-purple-darkness-a7qijg6z-pooler.ap-southeast-2.aws.neon.tech/neondb?ssl=require"
DB_URL = os.environ.get("DATABASE_URL", DEFAULT_DB_URL)
if DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
if "sslmode=require" in DB_URL:
    DB_URL = DB_URL.replace("sslmode=require", "ssl=require")

SHOWCASE_PROBLEMS = [
    {
        "id": 1,
        "title": "Two Sum",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Array", "Hash Table"],
        "statement": (
            "Given an array of integers `nums` and an integer `target`, return indices of the two numbers such that they add up to `target`.\n\n"
            "You may assume that each input would have exactly one solution, and you may not use the same element twice. You can return the answer in any order.\n\n"
            "### Example 1:\n"
            "**Input:** nums = [2,7,11,15], target = 9\n"
            "**Output:** [0,1]\n"
            "**Explanation:** Because nums[0] + nums[1] == 9, we return [0, 1].\n\n"
            "### Example 2:\n"
            "**Input:** nums = [3,2,4], target = 6\n"
            "**Output:** [1,2]\n\n"
            "### Constraints:\n"
            "- 2 <= nums.length <= 10^4\n"
            "- -10^9 <= nums[i] <= 10^9\n"
            "- -10^9 <= target <= 10^9\n"
            "- Only one valid answer exists."
        ),
        "test_cases": [
            {"input": "nums = [2, 7, 11, 15], target = 9", "output": "[0, 1]", "is_hidden": False},
            {"input": "nums = [3, 2, 4], target = 6", "output": "[1, 2]", "is_hidden": True},
            {"input": "nums = [3, 3], target = 6", "output": "[0, 1]", "is_hidden": True},
        ]
    },
    {
        "id": 2,
        "title": "Palindrome Number",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Math"],
        "statement": (
            "Given an integer `x`, return `true` if `x` is a palindrome, and `false` otherwise.\n\n"
            "An integer is a palindrome when it reads the same forward and backward. For example, 121 is a palindrome while 123 is not.\n\n"
            "### Example 1:\n"
            "**Input:** x = 121\n"
            "**Output:** true\n\n"
            "### Example 2:\n"
            "**Input:** x = -121\n"
            "**Output:** false\n"
            "**Explanation:** From left to right, it reads -121. From right to left, it becomes 121-. Therefore it is not a palindrome.\n\n"
            "### Constraints:\n"
            "- -2^31 <= x <= 2^31 - 1"
        ),
        "test_cases": [
            {"input": "x = 121", "output": "true", "is_hidden": False},
            {"input": "x = -121", "output": "false", "is_hidden": True},
            {"input": "x = 10", "output": "false", "is_hidden": True},
        ]
    },
    {
        "id": 3,
        "title": "Valid Parentheses",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["String", "Stack"],
        "statement": (
            "Given a string `s` containing just the characters '(', ')', '{', '}', '[' and ']', determine if the input string is valid.\n\n"
            "An input string is valid if:\n"
            "1. Open brackets must be closed by the same type of brackets.\n"
            "2. Open brackets must be closed in the correct order.\n"
            "3. Every close bracket has a corresponding open bracket of the same type.\n\n"
            "### Example 1:\n"
            "**Input:** s = '()[]{}'\n"
            "**Output:** true\n\n"
            "### Example 2:\n"
            "**Input:** s = '(]'\n"
            "**Output:** false\n\n"
            "### Constraints:\n"
            "- 1 <= s.length <= 10^4\n"
            "- `s` consists of parentheses only '()[]{}'."
        ),
        "test_cases": [
            {"input": "s = \"()[]{}\"", "output": "true", "is_hidden": False},
            {"input": "s = \"(]\"", "output": "false", "is_hidden": True},
            {"input": "s = \"([{}])\"", "output": "true", "is_hidden": True},
        ]
    },
    {
        "id": 4,
        "title": "Merge Two Sorted Lists",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Linked List", "Recursion"],
        "statement": (
            "You are given the heads of two sorted linked lists `list1` and `list2`.\n\n"
            "Merge the two lists into one sorted list. The list should be made by splicing together the nodes of the first two lists.\n\n"
            "Return the head of the merged linked list.\n\n"
            "### Example 1:\n"
            "**Input:** list1 = [1,2,4], list2 = [1,3,4]\n"
            "**Output:** [1,1,2,3,4,4]\n\n"
            "### Example 2:\n"
            "**Input:** list1 = [], list2 = []\n"
            "**Output:** []\n\n"
            "### Constraints:\n"
            "- The number of nodes in both lists is in the range [0, 50].\n"
            "- -100 <= Node.val <= 100\n"
            "- Both list1 and list2 are sorted in non-decreasing order."
        ),
        "test_cases": [
            {"input": "list1 = [1, 2, 4], list2 = [1, 3, 4]", "output": "[1, 1, 2, 3, 4, 4]", "is_hidden": False},
            {"input": "list1 = [], list2 = [0]", "output": "[0]", "is_hidden": True},
        ]
    },
    {
        "id": 5,
        "title": "Best Time to Buy and Sell Stock",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Array", "Dynamic Programming"],
        "statement": (
            "You are given an array `prices` where `prices[i]` is the price of a given stock on the `i`th day.\n\n"
            "You want to maximize your profit by choosing a single day to buy one stock and choosing a different day in the future to sell that stock.\n\n"
            "Return the maximum profit you can achieve from this transaction. If you cannot achieve any profit, return 0.\n\n"
            "### Example 1:\n"
            "**Input:** prices = [7,1,5,3,6,4]\n"
            "**Output:** 5\n"
            "**Explanation:** Buy on day 2 (price = 1) and sell on day 5 (price = 6), profit = 6-1 = 5.\n\n"
            "### Example 2:\n"
            "**Input:** prices = [7,6,4,3,1]\n"
            "**Output:** 0\n\n"
            "### Constraints:\n"
            "- 1 <= prices.length <= 10^5\n"
            "- 0 <= prices[i] <= 10^4"
        ),
        "test_cases": [
            {"input": "prices = [7, 1, 5, 3, 6, 4]", "output": "5", "is_hidden": False},
            {"input": "prices = [7, 6, 4, 3, 1]", "output": "0", "is_hidden": True},
        ]
    },
    {
        "id": 6,
        "title": "Maximum Subarray",
        "difficulty": ProblemDifficulty.MEDIUM,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Array", "Dynamic Programming", "Divide and Conquer"],
        "statement": (
            "Given an integer array `nums`, find the subarray with the largest sum, and return its sum.\n\n"
            "### Example 1:\n"
            "**Input:** nums = [-2,1,-3,4,-1,2,1,-5,4]\n"
            "**Output:** 6\n"
            "**Explanation:** The subarray [4,-1,2,1] has the largest sum 6.\n\n"
            "### Example 2:\n"
            "**Input:** nums = [5,4,-1,7,8]\n"
            "**Output:** 23\n\n"
            "### Constraints:\n"
            "- 1 <= nums.length <= 10^5\n"
            "- -10^4 <= nums[i] <= 10^4"
        ),
        "test_cases": [
            {"input": "nums = [-2, 1, -3, 4, -1, 2, 1, -5, 4]", "output": "6", "is_hidden": False},
            {"input": "nums = [5, 4, -1, 7, 8]", "output": "23", "is_hidden": True},
        ]
    },
    {
        "id": 7,
        "title": "Binary Search",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Array", "Binary Search"],
        "statement": (
            "Given an array of integers `nums` which is sorted in ascending order, and an integer `target`, write a function to search `target` in `nums`.\n\n"
            "If `target` exists, then return its index. Otherwise, return -1.\n\n"
            "You must write an algorithm with O(log n) runtime complexity.\n\n"
            "### Example 1:\n"
            "**Input:** nums = [-1,0,3,5,9,12], target = 9\n"
            "**Output:** 4\n\n"
            "### Example 2:\n"
            "**Input:** nums = [-1,0,3,5,9,12], target = 2\n"
            "**Output:** -1\n\n"
            "### Constraints:\n"
            "- 1 <= nums.length <= 10^4\n"
            "- -10^4 < nums[i], target < 10^4\n"
            "- All the integers in nums are unique.\n"
            "- nums is sorted in ascending order."
        ),
        "test_cases": [
            {"input": "nums = [-1, 0, 3, 5, 9, 12], target = 9", "output": "4", "is_hidden": False},
            {"input": "nums = [-1, 0, 3, 5, 9, 12], target = 2", "output": "-1", "is_hidden": True},
        ]
    },
    {
        "id": 8,
        "title": "Reverse Linked List",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Linked List", "Recursion"],
        "statement": (
            "Given the `head` of a singly linked list, reverse the list, and return the reversed list.\n\n"
            "### Example 1:\n"
            "**Input:** head = [1,2,3,4,5]\n"
            "**Output:** [5,4,3,2,1]\n\n"
            "### Example 2:\n"
            "**Input:** head = [1,2]\n"
            "**Output:** [2,1]\n\n"
            "### Constraints:\n"
            "- The number of nodes in the list is the range [0, 5000].\n"
            "- -5000 <= Node.val <= 5000"
        ),
        "test_cases": [
            {"input": "head = [1, 2, 3, 4, 5]", "output": "[5, 4, 3, 2, 1]", "is_hidden": False},
            {"input": "head = []", "output": "[]", "is_hidden": True},
        ]
    },
    {
        "id": 9,
        "title": "Climbing Stairs",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Math", "Dynamic Programming", "Memoization"],
        "statement": (
            "You are climbing a staircase. It takes `n` steps to reach the top.\n\n"
            "Each time you can either climb 1 or 2 steps. In how many distinct ways can you climb to the top?\n\n"
            "### Example 1:\n"
            "**Input:** n = 2\n"
            "**Output:** 2\n"
            "**Explanation:** There are two ways to climb to the top: 1 step + 1 step, or 2 steps.\n\n"
            "### Example 2:\n"
            "**Input:** n = 3\n"
            "**Output:** 3\n"
            "**Explanation:** 1+1+1, 1+2, 2+1.\n\n"
            "### Constraints:\n"
            "- 1 <= n <= 45"
        ),
        "test_cases": [
            {"input": "n = 2", "output": "2", "is_hidden": False},
            {"input": "n = 3", "output": "3", "is_hidden": True},
            {"input": "n = 5", "output": "8", "is_hidden": True},
        ]
    },
    {
        "id": 10,
        "title": "Invert Binary Tree",
        "difficulty": ProblemDifficulty.EASY,
        "time_limit": 1.0,
        "memory_limit": 256,
        "tags": ["Tree", "Binary Tree", "Breadth-First Search"],
        "statement": (
            "Given the `root` of a binary tree, invert the tree, and return its root.\n\n"
            "### Example 1:\n"
            "**Input:** root = [4,2,7,1,3,6,9]\n"
            "**Output:** [4,7,2,9,6,3,1]\n\n"
            "### Example 2:\n"
            "**Input:** root = [2,1,3]\n"
            "**Output:** [2,3,1]\n\n"
            "### Constraints:\n"
            "- The number of nodes in the tree is in the range [0, 100].\n"
            "- -100 <= Node.val <= 100"
        ),
        "test_cases": [
            {"input": "root = [4, 2, 7, 1, 3, 6, 9]", "output": "[4, 7, 2, 9, 6, 3, 1]", "is_hidden": False},
            {"input": "root = [2, 1, 3]", "output": "[2, 3, 1]", "is_hidden": True},
        ]
    }
]


async def seed_showcase():
    print(f"Connecting to database...")
    engine = create_async_engine(DB_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        for p_data in SHOWCASE_PROBLEMS:
            pid = p_data["id"]
            res = await session.execute(
                select(Problem).options(selectinload(Problem.tags)).where(Problem.problem_id == pid)
            )
            problem = res.scalar_one_or_none()

            if not problem:
                problem = Problem(
                    problem_id=pid,
                    title=p_data["title"],
                    statement_text=p_data["statement"],
                    difficulty=p_data["difficulty"],
                    time_limit=p_data["time_limit"],
                    memory_limit=p_data["memory_limit"],
                )
                session.add(problem)
            else:
                problem.title = p_data["title"]
                problem.statement_text = p_data["statement"]
                problem.difficulty = p_data["difficulty"]
                problem.time_limit = p_data["time_limit"]
                problem.memory_limit = p_data["memory_limit"]

            # Manage Tags
            tag_objects = []
            for t_name in p_data["tags"]:
                t_res = await session.execute(select(Tag).where(Tag.tag_name == t_name))
                t_obj = t_res.scalar_one_or_none()
                if not t_obj:
                    t_obj = Tag(tag_name=t_name)
                    session.add(t_obj)
                    await session.flush()
                tag_objects.append(t_obj)
            problem.tags = tag_objects

            # Clean and re-seed testcases
            await session.execute(delete(TestCase).where(TestCase.problem_id == pid))
            for tc in p_data["test_cases"]:
                new_tc = TestCase(
                    problem_id=pid,
                    input_text=tc["input"],
                    output_text=tc["output"],
                    is_hidden=tc["is_hidden"],
                )
                session.add(new_tc)

            print(f"  [+] Seeded Problem #{pid}: {p_data['title']} ({len(p_data['test_cases'])} test cases)")

        await session.commit()
    await engine.dispose()
    print("\n[SUCCESS] Top 10 Showcase problems seeded successfully with canonical data & testcases.")


if __name__ == "__main__":
    asyncio.run(seed_showcase())
