"""
Chat Agent Example - Demonstrates A2A communication with Action Agent

This example shows how a Chat Agent would communicate with the Action Agent
using the A2A (Agent-to-Agent) protocol.

Architecture:
  User → Chat Agent → [A2A] → Action Agent → MCP Servers → Results
"""

import asyncio
import httpx
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider


async def example_chat_agent_with_a2a_client():
    """
    Example: Chat Agent using A2A client to communicate with Action Agent.

    This demonstrates the recommended approach using A2AClientToolProvider.
    """
    print("=" * 70)
    print("  Chat Agent → Action Agent (A2A Client Example)")
    print("=" * 70)

    # Action Agent URL (where Action Agent A2A server is running)
    action_agent_url = "http://127.0.0.1:9000"

    print(f"\n1. Connecting to Action Agent at {action_agent_url}")

    # Create A2A client tool provider
    # This automatically discovers the Action Agent's capabilities
    a2a_provider = A2AClientToolProvider(
        known_agent_urls=[action_agent_url]
    )

    print("✓ Connected to Action Agent\n")

    # Create Chat Agent with Action Agent as a tool
    chat_agent = Agent(
        name="Chat Agent",
        tools=a2a_provider.tools,
        system_prompt="""You are a Chat Agent that helps users with identity and access management.

You have access to an Action Agent that can:
- Create and manage users in PingOne and Microsoft 365
- Assign groups and licenses
- Grant access to resources

When a user requests identity operations, use the Action Agent to execute them.
Provide clear, friendly responses to the user about what was done.
"""
    )

    print("2. Chat Agent initialized with Action Agent tools\n")

    # Simulate user requests
    user_requests = [
        "I need to create a new user john.doe@example.com for our Sales team",
        "Please assign John to the Sales group in Microsoft 365",
        "Grant John an E3 license"
    ]

    for i, user_request in enumerate(user_requests, 1):
        print(f"User Request {i}: {user_request}")
        print("-" * 70)

        # Chat Agent processes the request and calls Action Agent via A2A
        # Uncomment to execute (requires Action Agent server to be running)
        # response = await chat_agent.async_call(user_request)
        # print(f"Chat Agent Response: {response}\n")

        print("[Skipped - Requires Action Agent server running]\n")

    print("=" * 70)
    print("Example completed")
    print("=" * 70)


async def example_direct_a2a_communication():
    """
    Example: Direct A2A communication with Action Agent.

    This demonstrates lower-level A2A communication for advanced use cases.
    """
    print("\n" + "=" * 70)
    print("  Direct A2A Communication Example")
    print("=" * 70)

    from strands.multiagent.a2a import A2ACardResolver, ClientConfig, ClientFactory
    from strands.multiagent.a2a.protocol import Message, Role, Part, TextPart

    action_agent_url = "http://127.0.0.1:9000"

    print(f"\n1. Connecting to Action Agent at {action_agent_url}\n")

    async with httpx.AsyncClient(timeout=300.0) as http_client:
        # Step 1: Discover Action Agent capabilities
        resolver = A2ACardResolver(httpx_client=http_client, base_url=action_agent_url)

        # Uncomment to execute
        # agent_card = await resolver.get_agent_card()
        # print(f"Action Agent discovered:")
        # print(f"  Name: {agent_card.name}")
        # print(f"  Version: {agent_card.version}")
        # print(f"  Description: {agent_card.description}\n")

        print("2. Creating A2A client\n")

        # Step 2: Create A2A client
        config = ClientConfig(httpx_client=http_client, streaming=False)
        factory = ClientFactory(config)

        # Uncomment to execute
        # client = factory.create(agent_card)

        print("3. Sending message to Action Agent\n")

        # Step 3: Send message
        message = Message(
            role=Role.user,
            parts=[Part(TextPart(text="Create user jane.smith@example.com in PingOne"))]
        )

        # Uncomment to execute
        # async for event in client.send_message(message):
        #     print(f"Received: {event}")

        print("[Skipped - Requires Action Agent server running]\n")

    print("=" * 70)
    print("Example completed")
    print("=" * 70)


def example_chat_agent_scenario():
    """
    Example: Complete user onboarding scenario via Chat Agent → Action Agent.
    """
    print("\n" + "=" * 70)
    print("  Complete Onboarding Scenario")
    print("=" * 70)

    scenario = """
User: "I need to onboard a new employee, Sarah Johnson, as a Marketing Manager.
       Her email should be sarah.johnson@example.com"

Chat Agent (processes request) →
    Sends to Action Agent via A2A:
    "Create user sarah.johnson@example.com with the following details:
     - First Name: Sarah
     - Last Name: Johnson
     - Department: Marketing
     - Job Title: Marketing Manager

     Then assign her to:
     - Marketing Team group
     - All Employees group

     Grant access to:
     - Microsoft 365 E3 license
     - SharePoint Marketing site
     - Teams Marketing channel"

Action Agent (receives via A2A) →
    1. Validates request
    2. Creates user in PingOne (via MCP)
    3. Creates user in Microsoft 365 (via MCP)
    4. Assigns to groups (via MCP)
    5. Grants licenses and access (via MCP)
    6. Logs all actions
    7. Returns results via A2A

Chat Agent (receives results) →
    Formats friendly response for user:
    "✓ Successfully onboarded Sarah Johnson!

     Created accounts:
     - PingOne: user_abc123
     - Microsoft 365: user_xyz789

     Assigned groups:
     - Marketing Team
     - All Employees

     Granted access:
     - Microsoft 365 E3 license
     - SharePoint Marketing site
     - Teams Marketing channel

     Sarah can now access all required systems."
"""

    print(scenario)
    print("=" * 70)


async def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  Chat Agent ↔ Action Agent (A2A Examples)".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")

    # Example 1: A2A Client (Recommended)
    await example_chat_agent_with_a2a_client()

    # Example 2: Direct A2A (Advanced)
    await example_direct_a2a_communication()

    # Example 3: Complete Scenario
    example_chat_agent_scenario()

    print("\n" + "=" * 70)
    print("How to run these examples:")
    print("\n1. Start the Action Agent A2A server:")
    print("   python action_agent.py")
    print("\n2. In another terminal, run the Chat Agent:")
    print("   python chat_agent_example.py")
    print("\n3. Uncomment the execute calls in the examples above")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
