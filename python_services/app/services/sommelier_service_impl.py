from typing import List, Dict, Any, Callable, Literal
import json
import os
import re
import time
from openai import OpenAI
from ..common.api_stubs import SearchService, EmbeddingsService, PersistService
from ..common.api import (
    EmbeddingsSearchRequest, SearchRequest, Wine, GetWineRequest, GetWinesByUserIdRequest
)
StateCallback = Callable[[Literal["trace", "user"], str], None]

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
            print("OPENAI_API_KEY is set")
            self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        else:
            print("OPENAI_API_KEY is not set")
            self.client = None

    def _exact_search(self, 
                        query: str,
                        country: str = None,
                        variety: str = None,
                        winery: str = None,
                        price_range: Dict[str, float] = None,
                        points_range: Dict[str, int] = None,
                        sort_by: str = None,
                        sort_reverse: bool = False,
                        limit: int = 10) -> List[Wine]:
        numeric_ranges = {}
        if price_range:
            numeric_ranges["price"] = price_range
        if points_range:
            numeric_ranges["points"] = points_range
        
        filters = {}
        if country:
            filters["country"] = country
        if variety:
            filters["variety"] = variety
        if winery:
            filters["winery"] = winery

        search_request = SearchRequest(
            query=query,
            filters=filters or {},
            numeric_ranges=numeric_ranges,
            sort_by=sort_by,
            sort_reverse=sort_reverse,
            fuzzy=False,
            page=1,
            page_size=limit
        )
        response = self.search_service.catalog_search(search_request)
        if len(response.items) > 0:
            return self.persist_service.get_wine(GetWineRequest(ids=response.items))
        return []
  

    def _semantic_search(self, query: str, limit: int = 10) -> List[Wine]:
        embeddings_request = EmbeddingsSearchRequest(query=query, limit=limit)
        wine_ids = self.embeddings_service.catalog_search(embeddings_request)
        if len(wine_ids) > 0:
            return self.persist_service.get_wine(GetWineRequest(ids=wine_ids))
        return []

    def _format_wines_for_context(self, wines: List[Wine]):
        if not wines:
            return "No wines found."
        
        formatted_wines = []
        for wine in wines:
            wine_id = wine.id
            formatted_wines.append((
                f"- [Wine ID: {wine_id}] {wine.title} by {wine.winery} "
                f"{wine.variety} - ${wine.price}, "
                f"{wine.points} pts - {wine.country}, "
                f"{wine.province}"
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
- Provide specific wine recommendations with reasoning
-- Include educational content about wine regions, varieties, and characteristics
- Only return results that have been found either in the cellar, or by the tools
-- Try and return 5 wines total, including 2 from the user's cellar whenever possible
- Use the most appropriate tool to find results not in the cellar. 
-- For specific requests, use exact search. 
-- For semantic matching, use semantic search, but it's probably better to use exact search for specific requests first.
-- Feel free to use multiple tools in a single response and choose amongst the best results
- if the search tool returns poor results
-- Don't just return to the user telling them that are bad results. 
-- Call the tools again with a better query based on your knowledge. 
-- The user will only see your final response (i.e. one with no tool calls), so no need to apologize for earlier iterations.

IMPORTANT: When you recommend specific wines, please include their wine IDs in your response. For example:
"Here are my top new recommendations:
1. [Wine ID: 123] Château Margaux 2015 - A classic Bordeaux with...
2. [Wine ID: 456] Barolo Riserva 2018 - An exceptional Italian red..."

Here are my top recommendations already in your cellar:
3. [Wine ID: 123] Château Margaux 2015 - A classic Bordeaux with...
4. [Wine ID: 456] Barolo Riserva 2018 - An exceptional Italian red..."

This helps us provide the most accurate recommendations to the user.

Always format wine recommendations clearly and provide context about why you're recommending each wine."""

    def _create_ai_tools_schema(self) -> List[Dict[str, Any]]:
        """Create the tools schema for OpenAI function calling with advanced search capabilities"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "exact_search",
                    "description": "Text search with filtering, sorting, and highlighting. Use for complex queries with specific criteria.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (can be empty for pure filtering)"
                            },
                            "country": {
                                "type": "string",
                                "description": " the country of the wine"
                            },
                            "variety": {
                                "type": "string",
                                "description": "The variety of the wine"
                            },
                            "winery": {
                                "type": "string",
                                "description": "The winery of the wine"
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

    def _generate_search_intent(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        if tool_name == "exact_search":
            query = tool_args.get("query", "")
            summary_parts = [f"🔍 Searching for wines matching '{query}'"]
            country = tool_args.get("country")
            variety = tool_args.get("variety")
            winery = tool_args.get("winery")
            if country:
                summary_parts.append(f"from {country}")
            if variety:
                summary_parts.append(f"{variety} wines")
            if winery:
                summary_parts.append(f"from {winery}")
            
            price_range = tool_args.get("price_range")
            if price_range:
                min_price = price_range.get("min", 0)
                max_price = price_range.get("max", float('inf'))
                if max_price == float('inf'):
                    summary_parts.append(f"priced ${min_price}+")
                else:
                    summary_parts.append(f"priced ${min_price}-${max_price}")
                
            return " • ".join(summary_parts)
            
        elif tool_name == "semantic_search":
            query = tool_args.get("query", "")
            return f"🧠 Searching for wines semantically similar to '{query}'"
        
        return f"🔧 Using {tool_name} tool"

    def _generate_search_results(self, tool_name: str, tool_args: Dict[str, Any], tool_result: str) -> str:
        if tool_name == "exact_search":
            wines_found = len(tool_result.split('\n')) if tool_result != "No wines found." else 0
            if wines_found > 0:
                return f"✅ Found {wines_found} matching wines"
            else:
                return f"❌ No wines found matching criteria"
            
        elif tool_name == "semantic_search":
            query = tool_args.get("query", "")
            wines_found = len(tool_result.split('\n')) if tool_result != "No wines found." else 0
            if wines_found > 0:
                return f"✅ Found {wines_found} wines semantically similar to '{query}'"
            else:
                return f"❌ No wines found semantically similar to '{query}'"
        
        return f"🔧 {tool_name} tool completed"

    def _ai_chat(self, 
                  message: str, 
                  conversation_history: List[Dict[str, str]],
                  user_id: int | None = None,
                  state_callback: StateCallback = None) -> Dict[str, Any]:
        
        user_summaries = []
        def stream_trace(msg: str):
            timestamp = time.strftime("%H:%M:%S", time.localtime())
            if state_callback:
                state_callback("trace", f"[{timestamp}] {msg}")
        
        def stream_user_summary(summary: str):
            user_summaries.append(summary)
            if state_callback:
                state_callback("user", summary)

        cellar_wines = []
        cellar_context = ""
        if user_id:
            cellar_wines = self.persist_service.get_wines_by_user_id(GetWinesByUserIdRequest(user_id=user_id))
            cellar_context = f"\n\nUser's Cellar:\n{self._format_wines_for_context(cellar_wines)}"
        
        messages = [
            {"role": "system", "content": self._create_ai_system_prompt() + cellar_context},
        ]
        for msg in conversation_history[-100:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": message})
        
        all_found_wines = {}
        if cellar_wines:
            all_found_wines.update({wine.id: wine for wine in cellar_wines})
        count = 0
        stream_user_summary("Calling into LLM, iteration: " + str(count))

        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=self._create_ai_tools_schema(),
            tool_choice="auto",
            temperature=0.7,
            max_tokens=1500
        )
        assistant_message = response.choices[0].message
        while assistant_message.tool_calls and count < 5:
            stream_trace("Response is: " + str(response))
            messages.append(assistant_message)
            
            for tool_call in assistant_message.tool_calls:
                stream_trace("Calling: " + str(tool_call))
                    
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                stream_user_summary(self._generate_search_intent(tool_name, tool_args))
                
                if tool_name == "exact_search":
                    wines = self._exact_search(
                        query=tool_args.get("query", ""),
                        country=tool_args.get("country"),
                        variety=tool_args.get("variety"),
                        winery=tool_args.get("winery"),
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
                
                stream_trace("Tool result: \n" + str(tool_result))
                stream_user_summary(self._generate_search_results(tool_name, tool_args, tool_result))
                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": tool_call.id
                })
            count += 1
            stream_user_summary("Calling back into LLM, iteration: " + str(count))
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                tools=self._create_ai_tools_schema(),
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1500
            )
            assistant_message = response.choices[0].message
            
        stream_trace("Final response is: " + str(response))
        final_content = assistant_message.content
        recommended_wines = []
        if final_content:
            recommended_wine_ids = []
            wine_id_matches = re.findall(r'\[Wine ID:\s*(\d+)\]|\[ID:\s*(\d+)\]', final_content)
            stream_trace(f"Found {len(wine_id_matches)} wine ID matches in response")
            for match in wine_id_matches:
                wine_id = match[0] if match[0] else match[1]
                if wine_id:
                    recommended_wine_ids.append(int(wine_id))
                    stream_trace(f"Extracted wine ID: {wine_id}")
            
            stream_trace(f"All found wines keys: {list(all_found_wines.keys())}")
            if recommended_wine_ids:
                for wine_id in recommended_wine_ids:
                    if wine_id in all_found_wines:
                        recommended_wines.append(all_found_wines[wine_id])
                        stream_trace(f"Added wine {wine_id} to recommendations")
                    else:
                        stream_trace(f"Wine {wine_id} not found in all_found_wines")
            
            final_content = re.sub(r'\[Wine ID:\s*\d+\]|\[ID:\s*\d+\]', '', final_content)
            final_content = final_content.strip()
        else:
            final_content = "I'm sorry, I couldn't find any wines that match your request. Please try again with different criteria."
         
        return {
            "response": final_content,
            "recommended_wines": recommended_wines,
            "user_summaries": user_summaries
        }

    def _fallback_chat(self, message: str, state_callback: StateCallback = None) -> Dict[str, Any]:
        def stream_trace(msg: str):
            if state_callback:
                state_callback("trace", msg)
        
        def stream_user_summary(summary: str):
            if state_callback:
                state_callback("user", summary)
        
        stream_trace("Using fallback mode - LLM service unavailable")
        recommended_wines = self._semantic_search(message, 5)
        if len(recommended_wines) == 0:
            stream_trace("No semantic results found, trying text search")
            recommended_wines = self._exact_search(message, 5)
        
        if len(recommended_wines) > 0:
            stream_user_summary(f"🧠 Found {len(recommended_wines)} wines using semantic search for '{message}'")
        else:
            stream_user_summary(f"🔍 No wines found matching your request")
        
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
            "recommended_wines": recommended_wines[:10],
            "user_summaries": []
        }
           

    def chat(self, 
             message: str, 
             conversation_history: List[Dict[str, str]],
             user_id: int | None = None,
             state_callback: StateCallback = None) -> Dict[str, Any]:
        if not self.client:
            return self._fallback_chat(message, state_callback)
        else:
            return self._ai_chat(message, conversation_history, user_id, state_callback) 
