"""
Chart generation tools for creating visualizations
"""

import asyncio
import base64
import io
import time
from typing import Any, Dict, List, Optional, Union
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder

from .base import BaseTool, ToolResult, ToolStatus, ToolConfig


class ChartGeneratorTool(BaseTool):
    """Tool for generating various types of charts"""
    
    def __init__(self, name: str = "chart_generator", config: Optional[ToolConfig] = None):
        super().__init__(name, config)
        # Set matplotlib backend to avoid GUI issues
        plt.switch_backend('Agg')
    
    async def execute(self, **kwargs) -> ToolResult:
        """Generate chart based on data and parameters"""
        start_time = time.time()
        
        try:
            data = kwargs.get("data")
            chart_type = kwargs.get("chart_type", "line")
            title = kwargs.get("title", "Chart")
            x_column = kwargs.get("x_column")
            y_column = kwargs.get("y_column")
            output_format = kwargs.get("output_format", "base64")
            
            if not data:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Data is required"
                )
            
            self.logger.info(f"Generating {chart_type} chart: {title}")
            
            # Convert data to DataFrame if it's a list of dicts
            if isinstance(data, list) and data and isinstance(data[0], dict):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame(data)
            
            # Generate chart based on type
            if chart_type == "line":
                result = await self._generate_line_chart(df, title, x_column, y_column, output_format)
            elif chart_type == "bar":
                result = await self._generate_bar_chart(df, title, x_column, y_column, output_format)
            elif chart_type == "scatter":
                result = await self._generate_scatter_chart(df, title, x_column, y_column, output_format)
            elif chart_type == "pie":
                result = await self._generate_pie_chart(df, title, x_column, y_column, output_format)
            elif chart_type == "heatmap":
                result = await self._generate_heatmap(df, title, output_format)
            else:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error=f"Unsupported chart type: {chart_type}"
                )
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Chart generation error: {str(e)}",
                execution_time=execution_time
            )
    
    async def _generate_line_chart(self, df: pd.DataFrame, title: str, x_col: str, y_col: str, output_format: str) -> ToolResult:
        """Generate line chart"""
        try:
            # Use plotly for interactive charts
            if x_col and y_col:
                fig = px.line(df, x=x_col, y=y_col, title=title)
            else:
                # Use first two columns if not specified
                cols = df.columns.tolist()
                if len(cols) >= 2:
                    fig = px.line(df, x=cols[0], y=cols[1], title=title)
                else:
                    fig = px.line(df, title=title)
            
            if output_format == "base64":
                img_bytes = fig.to_image(format="png")
                img_base64 = base64.b64encode(img_bytes).decode()
                result_data = {"image": img_base64, "type": "line"}
            else:
                result_data = {"chart": fig.to_json(), "type": "line"}
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result_data,
                metadata={"chart_type": "line", "data_points": len(df)}
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Line chart error: {str(e)}"
            )
    
    async def _generate_bar_chart(self, df: pd.DataFrame, title: str, x_col: str, y_col: str, output_format: str) -> ToolResult:
        """Generate bar chart"""
        try:
            if x_col and y_col:
                fig = px.bar(df, x=x_col, y=y_col, title=title)
            else:
                cols = df.columns.tolist()
                if len(cols) >= 2:
                    fig = px.bar(df, x=cols[0], y=cols[1], title=title)
                else:
                    fig = px.bar(df, title=title)
            
            if output_format == "base64":
                img_bytes = fig.to_image(format="png")
                img_base64 = base64.b64encode(img_bytes).decode()
                result_data = {"image": img_base64, "type": "bar"}
            else:
                result_data = {"chart": fig.to_json(), "type": "bar"}
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result_data,
                metadata={"chart_type": "bar", "data_points": len(df)}
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Bar chart error: {str(e)}"
            )
    
    async def _generate_scatter_chart(self, df: pd.DataFrame, title: str, x_col: str, y_col: str, output_format: str) -> ToolResult:
        """Generate scatter plot"""
        try:
            if x_col and y_col:
                fig = px.scatter(df, x=x_col, y=y_col, title=title)
            else:
                cols = df.columns.tolist()
                if len(cols) >= 2:
                    fig = px.scatter(df, x=cols[0], y=cols[1], title=title)
                else:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.FAILED,
                        error="Scatter plot requires at least 2 columns"
                    )
            
            if output_format == "base64":
                img_bytes = fig.to_image(format="png")
                img_base64 = base64.b64encode(img_bytes).decode()
                result_data = {"image": img_base64, "type": "scatter"}
            else:
                result_data = {"chart": fig.to_json(), "type": "scatter"}
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result_data,
                metadata={"chart_type": "scatter", "data_points": len(df)}
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Scatter chart error: {str(e)}"
            )
    
    async def _generate_pie_chart(self, df: pd.DataFrame, title: str, x_col: str, y_col: str, output_format: str) -> ToolResult:
        """Generate pie chart"""
        try:
            if x_col and y_col:
                fig = px.pie(df, names=x_col, values=y_col, title=title)
            else:
                cols = df.columns.tolist()
                if len(cols) >= 2:
                    fig = px.pie(df, names=cols[0], values=cols[1], title=title)
                else:
                    return ToolResult(
                        tool_name=self.name,
                        status=ToolStatus.FAILED,
                        error="Pie chart requires at least 2 columns"
                    )
            
            if output_format == "base64":
                img_bytes = fig.to_image(format="png")
                img_base64 = base64.b64encode(img_bytes).decode()
                result_data = {"image": img_base64, "type": "pie"}
            else:
                result_data = {"chart": fig.to_json(), "type": "pie"}
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result_data,
                metadata={"chart_type": "pie", "data_points": len(df)}
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Pie chart error: {str(e)}"
            )
    
    async def _generate_heatmap(self, df: pd.DataFrame, title: str, output_format: str) -> ToolResult:
        """Generate heatmap"""
        try:
            # For heatmap, we need numeric data
            numeric_df = df.select_dtypes(include=['number'])
            if numeric_df.empty:
                return ToolResult(
                    tool_name=self.name,
                    status=ToolStatus.FAILED,
                    error="Heatmap requires numeric data"
                )
            
            fig = px.imshow(numeric_df, title=title)
            
            if output_format == "base64":
                img_bytes = fig.to_image(format="png")
                img_base64 = base64.b64encode(img_bytes).decode()
                result_data = {"image": img_base64, "type": "heatmap"}
            else:
                result_data = {"chart": fig.to_json(), "type": "heatmap"}
            
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.COMPLETED,
                result=result_data,
                metadata={"chart_type": "heatmap", "data_points": len(df)}
            )
            
        except Exception as e:
            return ToolResult(
                tool_name=self.name,
                status=ToolStatus.FAILED,
                error=f"Heatmap error: {str(e)}"
            )
