"""
Example usage of the Action Agent

This script demonstrates how to use the Action Agent for various
identity and access management tasks.
"""

import os
import asyncio
from action_agent import ActionAgent


def example_sync_usage():
    """Demonstrate synchronous usage of the Action Agent."""

    print("=" * 60)
    print("Action Agent - Synchronous Usage Example")
    print("=" * 60)

    # Initialize the Action Agent
    print("\n1. Initializing Action Agent...")
    agent = ActionAgent(
        model_provider=os.getenv("MODEL_PROVIDER", "bedrock"),
        model_id=os.getenv("MODEL_ID", "us.amazon.nova-pro-v1:0"),
        temperature=0.3
    )
    print("✓ Action Agent initialized")

    # Example 1: Create a new user
    print("\n2. Example: Create new user")
    print("-" * 60)
    instruction = """
    Create a new user with the following details:
    - Email: john.doe@example.com
    - First Name: John
    - Last Name: Doe
    - Department: Sales
    - Job Title: Sales Representative

    Create this user in PingOne.
    """
    print(f"Instruction: {instruction.strip()}")

    # Uncomment to execute (requires MCP servers to be running)
    # response = agent.execute(instruction)
    # print(f"\nResponse: {response}")
    print("\n[Skipped - Enable by uncommenting the execute call]")

    # Example 2: Assign user to groups
    print("\n3. Example: Assign user to groups")
    print("-" * 60)
    instruction = """
    Add the user john.doe@example.com to the following groups:
    - Sales Team (in Microsoft 365)
    - All Employees (in Microsoft 365)

    Ensure the user has appropriate access.
    """
    print(f"Instruction: {instruction.strip()}")
    print("\n[Skipped - Enable by uncommenting the execute call]")

    # Example 3: Grant specific access
    print("\n4. Example: Grant access to resources")
    print("-" * 60)
    instruction = """
    Grant the following access to john.doe@example.com:
    - Microsoft 365 E3 license
    - SharePoint Sales site (read/write)
    - Teams: Sales Team channel

    Execute these access grants and confirm completion.
    """
    print(f"Instruction: {instruction.strip()}")
    print("\n[Skipped - Enable by uncommenting the execute call]")

    print("\n" + "=" * 60)
    print("Synchronous examples completed")
    print("=" * 60)


async def example_async_usage():
    """Demonstrate asynchronous usage of the Action Agent."""

    print("\n" + "=" * 60)
    print("Action Agent - Asynchronous Usage Example")
    print("=" * 60)

    # Initialize the Action Agent
    print("\n1. Initializing Action Agent...")
    agent = ActionAgent(
        model_provider=os.getenv("MODEL_PROVIDER", "bedrock"),
        model_id=os.getenv("MODEL_ID", "us.amazon.nova-pro-v1:0"),
        temperature=0.3
    )
    print("✓ Action Agent initialized")

    # Example: Complex multi-step operation
    print("\n2. Example: Onboard new employee (async)")
    print("-" * 60)
    instruction = """
    Onboard new employee with the following steps:
    1. Create user account in PingOne
       - Email: jane.smith@example.com
       - First Name: Jane
       - Last Name: Smith
       - Department: Engineering
       - Job Title: Software Engineer

    2. Create user in Microsoft 365

    3. Assign to groups:
       - Engineering Team
       - All Employees

    4. Grant access:
       - Microsoft 365 E3 license
       - GitHub Enterprise access
       - Jira access

    Execute all steps and provide a summary of what was completed.
    """
    print(f"Instruction: {instruction.strip()}")

    # Uncomment to execute (requires MCP servers to be running)
    # response = await agent.execute_async(instruction)
    # print(f"\nResponse: {response}")
    print("\n[Skipped - Enable by uncommenting the execute_async call]")

    print("\n" + "=" * 60)
    print("Asynchronous examples completed")
    print("=" * 60)


def example_coordinator_integration():
    """Demonstrate how the Coordinator Agent would use the Action Agent."""

    print("\n" + "=" * 60)
    print("Action Agent - Coordinator Integration Example")
    print("=" * 60)

    print("""
This example shows how the Coordinator Agent would interact with the Action Agent.

Typical Flow:
1. Coordinator receives request from HR
2. Coordinator validates with Policy Agent
3. Coordinator gets approval (if required)
4. Coordinator sends signed instruction to Action Agent
5. Action Agent executes and returns result
6. Coordinator logs and notifies requester
    """)

    # Simulated instruction from Coordinator
    coordinator_instruction = {
        "request_id": "REQ-2024-001",
        "requester": "hr@example.com",
        "approval_id": "APR-2024-123",
        "timestamp": "2024-01-15T10:30:00Z",
        "action": "onboard_employee",
        "target": {
            "email": "new.hire@example.com",
            "first_name": "New",
            "last_name": "Hire",
            "department": "Marketing",
            "role": "Marketing Manager",
            "manager": "manager@example.com"
        },
        "access_package": {
            "groups": ["Marketing Team", "All Employees"],
            "licenses": ["Microsoft 365 E3"],
            "applications": ["Salesforce", "HubSpot"],
            "resources": ["SharePoint Marketing Site"]
        },
        "signature": "signed_hash_from_coordinator"
    }

    print(f"\nCoordinator Instruction:\n{coordinator_instruction}")

    print("""
Action Agent would:
1. Validate the signature
2. Validate the request structure
3. Execute each operation through MCP servers
4. Log each action
5. Return comprehensive result to Coordinator
    """)

    print("\n" + "=" * 60)
    print("Integration example completed")
    print("=" * 60)


def main():
    """Run all examples."""

    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  Action Agent - Usage Examples".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "═" * 58 + "╝")

    # Run synchronous examples
    example_sync_usage()

    # Run asynchronous examples
    asyncio.run(example_async_usage())

    # Show coordinator integration
    example_coordinator_integration()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("\nNote: To actually execute instructions, you need to:")
    print("  1. Set up PingOne and Microsoft Graph MCP servers")
    print("  2. Configure your .env file with credentials")
    print("  3. Uncomment the execute() calls in the examples")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
