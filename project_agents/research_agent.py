from agents import Agent, WebSearchTool
import logging


class ResearchAgent(Agent):
    """
    Research agent equipped with web search capability for factual information retrieval.
    """

    def __init__(self) -> None:
        """
        Initialize the Research Agent with specific instructions and tools.
        """
        super().__init__(
            name="Research Agent",
            instructions=(
                "You are a research assistant. Your task is to use the web search tool to find "
                "relevant, recent, and factual information on topics provided to you, focusing on "
                "AI, LLMs, and Machine Learning. Summarize your findings concisely."
            ),
            model="gpt-4.1",
            tools=[WebSearchTool()],
        )
        self.logger = logging.getLogger(__name__) 