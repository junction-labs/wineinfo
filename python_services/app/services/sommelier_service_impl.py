from typing import List, Dict, Any
import json
import os
from openai import OpenAI
from ..common.api_stubs import SearchService, EmbeddingsService, PersistService
from ..common.api import (
    GetWineRequest, EmbeddingsSearchRequest, SearchRequest, Wine
)
import re


class SommelierServiceImpl:
    def __init__(self, 
                 persist_service: PersistService, 
                 search_service: SearchService,
                 embeddings_service: EmbeddingsService,
                 ): 
        self.persist_service = persist_service
        self.search_service = search_service
        self.embeddings_service = embeddings_service
        
        if os.getenv("OPENAI_API_KEY"):
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            self.client = None

    def _text_search(self, 
                        query: str,
                        filters: Dict[str, Any] = None,
                        price_range: Dict[str, float] = None,
                        points_range: Dict[str, int] = None,
                        sort_by: str = None,
                        sort_reverse: bool = False,
                        fuzzy: bool = False,
                        limit: int = 10) -> List[Wine]:
        numeric_ranges = {}
        if price_range:
            numeric_ranges["price"] = price_range
        if points_range:
            numeric_ranges["points"] = points_range
        
        search_request = SearchRequest(
            query=query,
            filters=filters or {},
            numeric_ranges=numeric_ranges,
            sort_by=sort_by,
            sort_reverse=sort_reverse,
            fuzzy=fuzzy,
            page=1,
            page_size=limit
        )
        result = self.search_service.catalog_search(search_request)
        if len(result.items) > 0:
            return self.persist_service.get_wine(GetWineRequest(ids=result.items))
        return []
  

    def _semantic_search(self, query: str, limit: int = 10) -> List[Wine]:
        embeddings_request = EmbeddingsSearchRequest(query=query, limit=limit)
        result = self.embeddings_service.catalog_search(embeddings_request)
        if result:
            return self.persist_service.get_wine(GetWineRequest(ids=result))
        return []

    def _format_wines_for_context(self, wines: List[Dict[str, Any]]):
        if not wines:
            return "No wines found."
        
        formatted_wines = []
        for wine in wines:
            wine_id = wine.get('id', 'Unknown')
            formatted_wines.append((
                f"- [Wine ID: {wine_id}] {wine.get('title', 'Unknown')} by {wine.get('winery', 'Unknown')} "
                f"({wine.get('variety', 'Unknown')}) - ${wine.get('price', '0')}, "
                f"{wine.get('points', '0')} pts - {wine.get('country', 'Unknown')}, "
                f"{wine.get('province', 'Unknown')}"
            ))
        return "\n".join(formatted_wines)
    
    def _create_ai_system_prompt(self) -> str:
        """Create the system prompt for the AI agent"""
        return """You are an expert sommelier and wine advisor with access to a comprehensive wine database and advanced search tools. You have access to:

1. **Semantic Search**: Semantic search for wine using a description
2. **Text Search**: Powerful text search with filtering, sorting, and filtering


Your role is to:
- Understand the user's wine preferences, budget, occasion, and food pairings
- Use the search tools to find the best recommendations
- Provide detailed, knowledgeable wine advice with specific reasoning
- Explain wine characteristics, regions, and pairing suggestions
- Be conversational and educational while being helpful

When responding:
- only return results that have been found by the search tools in this conversation
- Use the most appropriate search tool for each query
- For specific requests, use text search
- For semantic matching, use semantic search
- Provide specific wine recommendations with reasoning
- Include educational content about wine regions, varieties, and characteristics
- Consider food pairings when relevant
- Mention if the user already has good wines in their cellar

IMPORTANT: When you recommend specific wines, please include their wine IDs in your response. For example:
"Here are my top recommendations:
1. [Wine ID: 123] Château Margaux 2015 - A classic Bordeaux with..."
2. [Wine ID: 456] Barolo Riserva 2018 - An exceptional Italian red..."

This helps us provide the most accurate recommendations to the user.

Always format wine recommendations clearly and provide context about why you're recommending each wine."""

    def _create_ai_tools_schema(self) -> List[Dict[str, Any]]:
        """Create the tools schema for OpenAI function calling with advanced search capabilities"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "text_search",
                    "description": "Text search with filtering, sorting, and highlighting. Use for complex queries with specific criteria.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (can be empty for pure filtering)"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Field filters (e.g., {'country': 'France', 'variety': 'Cabernet Sauvignon'})"
                            },
                            "price_range": {
                                "type": "object",
                                "description": "Price range filter (e.g., {'min': 20, 'max': 100})"
                            },
                            "sort_by": {
                                "type": "string",
                                "description": "Field to sort by ('price', 'points', or leave empty for relevance)"
                            },
                            "sort_reverse": {
                                "type": "boolean",
                                "description": "Reverse sort order (true for descending)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of wines to return (default 10)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "semantic_search",
                    "description": "Semantic search for wine recommendations based on descriptions and preferences.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Description of desired wine characteristics or preferences"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of recommendations to return (default 10)"
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def _ai_chat(self, 
                  message: str, 
                  conversation_history: List[Dict[str, str]], 
                  cellar_wine_ids: List[int]) -> Dict[str, Any]:

        cellar_wines = []
        cellar_context = ""
        if cellar_wine_ids:
            cellar_wines = self.persist_service.get_wine(GetWineRequest(ids=cellar_wine_ids))
            cellar_context = f"\n\nUser's Cellar:\n{self._format_wines_for_context(cellar_wines)}"
        
        messages = [
            {"role": "system", "content": self._create_ai_system_prompt() + cellar_context},
        ]
        for msg in conversation_history[-100:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})
                
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=self._create_ai_tools_schema(),
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1500
        )
        assistant_message = response.choices[0].message

        trace = []
        all_found_wines = {}
        count = 0
        while assistant_message.tool_calls and count < 5:  # Increased tool call limit
            trace.append("TRACE: On iteration: " + str(count))
            trace.append("TRACE: The last response is: " + str(response.choices[0]))
            messages.append(assistant_message)
            count += 1
            for tool_call in assistant_message.tool_calls:
                trace.append("TRACE: Calling a tool: " + str(tool_call))
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                
                if tool_name == "text_search":
                    wines = self._text_search(
                        query=tool_args.get("query", ""),
                        filters=tool_args.get("filters"),
                        price_range=tool_args.get("price_range"),
                        sort_by=tool_args.get("sort_by"),
                        sort_reverse=tool_args.get("sort_reverse", False),
                        limit=tool_args.get("limit", 10)
                    )
                    tool_result = self._format_wines_for_context(wines)
                    all_found_wines.update({wine.id: wine for wine in wines})
                elif tool_name == "semantic_search":
                    wines = self._semantic_search(tool_args["query"], tool_args.get("limit", 10))
                    tool_result = self._format_wines_for_context(wines)
                    all_found_wines.update({wine.id: wine for wine in wines})
                else:
                    tool_result = "Tool not available"
                trace.append("TRACE: Tool result: \n" + str(tool_result))

                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": tool_call.id
                })
            
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=self._create_ai_tools_schema(),
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500
            )
            assistant_message = response.choices[0].message
            
        final_content = assistant_message.content
        
        recommended_wines = []
        if final_content:
            recommended_wine_ids = []
            wine_id_matches = re.findall(r'\[Wine ID:\s*(\d+)\]|\[ID:\s*(\d+)\]', final_content)
            for match in wine_id_matches:
                wine_id = match[0] if match[0] else match[1]
                if wine_id:
                    recommended_wine_ids.append(int(wine_id))
            
            if recommended_wine_ids:
                for wine in cellar_wines:
                    if wine.get('id'):
                        all_found_wines[wine.get('id')] = wine
                for wine_id in recommended_wine_ids:
                    if wine_id in all_found_wines:
                        recommended_wines.append(all_found_wines[wine_id])
            
            final_content = re.sub(r'\[Wine ID:\s*\d+\]|\[ID:\s*\d+\]', '', final_content)
            final_content = re.sub(r'\s+', ' ', final_content).strip()
        else:
            final_content = "I'm sorry, I couldn't find any wines that match your request. Please try again with different criteria."
         
        return {
            "response": final_content,
            "recommended_wines": recommended_wines
        }

    def _fallback_chat(self, message: str) -> Dict[str, Any]:
        """A simulated sommelier chat for when the LLM service is unavailable"""
        recommended_wines = self._semantic_search(message, 5)
        if len(recommended_wines) == 0:
            recommended_wines = self._text_search(message, 5)
              
        if len(recommended_wines) > 0:
            if "budget" in message.lower() or "cheap" in message.lower():
                response = f"Here are some great value wines I found based on your request. These selections offer excellent quality for their price point."
            elif "red" in message.lower():
                response = f"I found some excellent red wines that match your preferences. These reds offer different flavor profiles to explore."
            elif "white" in message.lower():
                response = f"Here are some wonderful white wines I'd recommend. These whites offer various styles from crisp to rich."
            elif "food" in message.lower() or "pair" in message.lower():
                response = f"Based on your food pairing request, here are some versatile wines. These wines are excellent for food pairing."
            else:
                response = f"Based on your preferences, I recommend these wines. Each offers unique characteristics that align with what you're looking for."
            
            response += "\n\n*Note: I'm currently running in simplified mode. For more detailed wine advice and sommelier insights, please configure the OpenAI integration.*"
        else:
            response = "I'd be happy to help you find the perfect wine! Please tell me what you're looking for - wine style, price range, occasion, or regions you enjoy.\n\n*Note: I'm currently running in simplified mode. For more detailed wine advice and sommelier insights, please configure the OpenAI integration.*"
        
        return {
            "response": response,
            "recommended_wines": recommended_wines[:10]  # Return the actual wine objects directly
        }
           

    def chat(self, 
             message: str, 
             conversation_history: List[Dict[str, str]], 
             cellar_wine_ids: List[int]) -> Dict[str, Any]:
        if not self.client:
            return self._fallback_chat(message)
        else:
            return self._ai_chat(message, conversation_history, cellar_wine_ids) 
