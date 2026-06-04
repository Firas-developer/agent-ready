"""Unified LLM client — supports Claude, OpenAI, Azure OpenAI, Azure Foundry Claude."""
import os
from typing import Optional


class LLMClient:
    """Single interface for all supported LLM providers.

    Providers:
        claude               → direct Anthropic API (ANTHROPIC_API_KEY)
        openai               → direct OpenAI API (OPENAI_API_KEY)
        azure_openai         → Azure OpenAI endpoint (AZURE_OPENAI__API_KEY + AZURE_OPENAI__BASE_URL)
        azure_foundry_claude → Claude via Azure AI Foundry (ANTHROPIC_FOUNDRY__API_KEY + resource)

    Usage:
        client = LLMClient(provider="azure_foundry_claude")
        response = client.complete(system, user)
    """

    def __init__(self, provider: str = "azure_foundry_claude", model: Optional[str] = None):
        self.provider = provider

        if provider == "claude":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            self.model = model or "claude-sonnet-4-6"

        elif provider == "openai":
            from openai import OpenAI
            self.client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            self.model = model or "gpt-4o"

        elif provider == "azure_openai":
            from openai import OpenAI
            base_url = os.environ["AZURE_OPENAI__BASE_URL"]
            api_key = os.environ["AZURE_OPENAI__API_KEY"]
            # Azure OpenAI /openai/v1/ endpoint is OpenAI-API-compatible
            self.client = OpenAI(base_url=base_url, api_key=api_key)
            self.model = model or os.environ.get("AZURE_OPENAI__DEPLOYMENT", "gpt-4o")

        elif provider == "azure_foundry_claude":
            from anthropic import AnthropicFoundry
            
            api_key = os.environ.get("ANTHROPIC_FOUNDRY__API_KEY", "")
            resource = os.environ.get("ANTHROPIC_FOUNDRY__RESOURCE", "")
            deployment = os.environ.get("ANTHROPIC_FOUNDRY__DEPLOYMENT_NAME", "claude-haiku-4-5")
            
            print(f"\n🔍 Azure AI Foundry Debug:")
            print(f"  API Key present: {bool(api_key)}")
            print(f"  API Key length: {len(api_key)}")
            print(f"  Resource: {resource}")
            print(f"  Deployment: {deployment}")
            
            if not api_key:
                raise ValueError("ANTHROPIC_FOUNDRY__API_KEY is empty in .env file!")
            if not resource:
                raise ValueError("ANTHROPIC_FOUNDRY__RESOURCE is empty in .env file!")
            
            self.client = AnthropicFoundry(
                api_key=api_key,
                resource=resource,
            )
            self.model = model or deployment
            
            print(f"  Using model: {self.model}\n")


        else:
            raise ValueError(
                f"Unsupported provider '{provider}'. "
                "Use: claude | openai | azure_openai | azure_foundry_claude"
            )

    def complete(self, system: str, user: str, max_tokens: int = 4096) -> str:
        """Send system + user prompt and return the text response."""
        if self.provider in ("claude", "azure_foundry_claude"):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return response.content[0].text

        elif self.provider in ("openai", "azure_openai"):
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            return response.choices[0].message.content

        return ""
