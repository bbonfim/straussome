"""
Report Generation Agent - Creates comprehensive reports from analysis and charts
"""

import asyncio
import logging
import time
from typing import Any, Dict, Optional

from .base import BaseAgent, AgentState

logger = logging.getLogger(__name__)


class ReportGenerationAgent(BaseAgent):
    """Agent that generates final reports"""
    
    def __init__(self, agent_id: str, config: Optional[Dict[str, Any]] = None, tool_registry=None):
        super().__init__(agent_id, config, tool_registry)
    
    async def execute(self, state: AgentState) -> AgentState:
        """Generate final report"""
        self.logger.info(f"Starting report generation for task {state.task_id}")
        
        try:
            # Get results from previous agents
            analysis_result = state.shared_data.get("data_analyzer_result", {})
            charts_result = state.shared_data.get("chart_generator_result", {})
            
            # Simulate report generation
            await asyncio.sleep(0.2)  # Simulate processing time
            
            # Generate comprehensive report
            report = {
                "task_id": state.task_id,
                "generated_at": time.time(),
                "executive_summary": {
                    "total_records_analyzed": analysis_result.get("total_records", 0),
                    "key_insights": analysis_result.get("insights", []),
                    "charts_generated": len(charts_result)
                },
                "detailed_analysis": analysis_result,
                "visualizations": charts_result,
                "recommendations": [
                    "Continue monitoring category B trends",
                    "Investigate outliers in value distribution",
                    "Consider automated reporting for regular updates"
                ],
                "metadata": {
                    "agents_used": ["data_analyzer", "chart_generator", "report_generator"],
                    "processing_time": "~1 second",
                    "data_quality": "high"
                }
            }
            
            # Store final result
            state.shared_data[f"{self.agent_id}_result"] = report
            state.shared_data["report_complete"] = True
            state.shared_data["final_result"] = report
            
            self.logger.info(f"Report generation completed for task {state.task_id}")
            return state
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {e}")
            raise
