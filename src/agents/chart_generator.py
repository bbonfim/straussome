"""
Chart Generation Agent - Creates visualizations from analyzed data
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from .base import BaseAgent, AgentState

logger = logging.getLogger(__name__)


class ChartGenerationAgent(BaseAgent):
    """Agent that generates charts from analyzed data"""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None, tool_registry=None):
        super().__init__(agent_id, config, tool_registry)
    
    async def execute(self, state: AgentState) -> AgentState:
        """Generate charts from data"""
        self.logger.info(f"Starting chart generation for task {state.task_id}")
        
        try:
            # Check if analysis is complete
            if not state.shared_data.get("analysis_complete"):
                raise ValueError("Data analysis must be completed before chart generation")
            
            # Get analysis result from previous agent
            analysis_result = state.shared_data.get("data_analyzer_result", {})
            
            charts = {}
            
            # Use chart generator tool if available
            if self.tool_registry:
                chart_tool = self.tool_registry.get("chart_generator")
                if chart_tool:
                    self.logger.info("Generating charts using ChartGeneratorTool")
                    
                    # Generate bar chart from user distribution
                    user_dist_chart = analysis_result.get("user_distribution_chart", [])

                    if user_dist_chart:
                        bar_result = await chart_tool.execute(
                            data=user_dist_chart,
                            chart_type="bar",
                            title="User Post Distribution",
                            x_column="User ID",
                            y_column="Posts"
                        )
                        self.logger.info(f"Bar result: {bar_result}")
                        if bar_result.status.value == "completed":
                            charts["user_distribution_bar"] = {
                                "type": "bar",
                                "title": "User Post Distribution",
                                "data": bar_result.result,
                                "chart_id": f"chart_{state.task_id}_user_dist"
                            }
                    
                    # Generate line chart for trends
                    line_result = await chart_tool.execute(
                        data=[{"x": i, "y": 10 + i * 2} for i in range(10)],
                        chart_type="line",
                        title="Sample Trend Analysis",
                        x_column="Time",
                        y_column="Value"
                    )
                    
                    if line_result.status.value == "completed":
                        charts["trend_line"] = {
                            "type": "line",
                            "title": "Sample Trend Analysis",
                            "data": line_result.result,
                            "chart_id": f"chart_{state.task_id}_trend"
                        }
                    
                    self.logger.info(f"Generated {len(charts)} charts using ChartGeneratorTool")
                else:
                    self.logger.warning("ChartGeneratorTool not available, using mock charts")
                    charts = self._get_mock_charts(analysis_result, state.task_id)
            else:
                self.logger.warning("No tool registry available, using mock charts")
                charts = self._get_mock_charts(analysis_result, state.task_id)
            
            # Store result
            state.shared_data[f"{self.agent_id}_result"] = charts
            state.shared_data["charts_generated"] = True
            self.logger.info(f"Results from chart generation: {charts}")
            self.logger.info(f"Chart generation completed for task {state.task_id}")
            return state
            
        except Exception as e:
            self.logger.error(f"Chart generation failed: {e}")
            raise
    
    def _get_mock_charts(self, analysis_result: dict, task_id: str) -> dict:
        """Generate mock chart data as fallback"""
        return {
            "bar_chart": {
                "type": "bar",
                "title": "Category Distribution",
                "data": analysis_result.get("category_distribution", {"A": 300, "B": 400, "C": 300}),
                "chart_id": f"chart_{task_id}_bar"
            },
            "line_chart": {
                "type": "line",
                "title": "Value Trends",
                "data": [{"x": i, "y": 100 + i * 2} for i in range(10)],
                "chart_id": f"chart_{task_id}_line"
            }
        }
