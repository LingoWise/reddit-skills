SUBREDDIT_SUGGEST_PROMPT = """Given the topic below and the Reddit posts provided, suggest 3-5 relevant subreddits where a post about this topic would fit naturally. Return a single JSON object with one key "subreddits" containing a list of strings like "r/AskReddit". Do not explain.

Topic: {topic}

Reddit posts:
{corpus}
"""

RESEARCH_PROMPT = """You are a Reddit content strategist. Analyze the top posts below and summarize what makes them successful in this community.

Topic: {topic}
Target subreddit: {subreddit}

Return a single JSON object with these keys:
- "hook_patterns": list of common title structures or hooks
- "title_length": "short", "medium", or "long"
- "tone": one word describing the dominant tone
- "high_engagement_themes": list of themes that get attention

Be concise. Do not include markdown or explanation.

Reddit posts:
{corpus}
"""

DRAFT_PROMPT = """You are a native Reddit contributor. Write a post for r/{subreddit} about the topic below.

Topic: {topic}
Style: {style}
Language: {language}

Rules:
- Do NOT sound like an advertisement, marketer, or salesperson.
- Match the style requested.
- Use the research patterns below to fit the community.
- Write in the requested language.
- Keep the tone natural and community-native.

Research patterns:
{patterns}

Return a single JSON object with these keys:
- "title": the post title (max 300 chars)
- "body": the post body or caption (use empty string if style is "image-only")
- "kind": one of "self", "link", "image" (infer from content)
- "url": external URL, only if kind is "link"
- "image_prompt": a detailed image generation prompt, only if kind is "image"
- "inspiration": list of URLs from the research that influenced the post

Only return valid JSON. No markdown, no explanation.
"""
