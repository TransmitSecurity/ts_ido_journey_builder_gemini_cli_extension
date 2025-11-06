#!/usr/bin/env python3
"""
Journey Structure Validator

Validates journey structural integrity:
- UUID formats (node IDs, workflow ID)
- Node types (valid node types)
- Journey completeness (all nodes reachable from head)
- Loop and block body structure
- Loop references (prevents editor freeze)
- Link structure (required fields)
"""

import re
from typing import List, Set

from journey_validator_base import JourneyValidatorBase


class JourneyStructureValidator(JourneyValidatorBase):
    """Validates journey structural integrity."""

    def get_validator_name(self) -> str:
        return "Journey Structure Validation"

    def run_validations(self) -> None:
        """Run structure-specific validations."""
        # Extract workflow first
        if not self.extract_workflow(required=True):
            return  # Errors already added by extract_workflow

        print("✓ UUID validation")
        self.validate_uuids()

        print("✓ Node type validation")
        self.validate_node_types()

        print("✓ Journey completeness validation")
        self.validate_journey_completeness()

        print("✓ Loop and block body validation")
        self.validate_loop_and_block_body()

        print("✓ Loop reference validation (prevents editor freeze)")
        self.validate_loop_references()

        print("✓ Link structure validation")
        self.validate_link_structure()

        print("✓ Terminal node validation")
        self.validate_terminal_nodes()

        print("✓ Required links validation")
        self.validate_required_links()

    @staticmethod
    def is_valid_uuid(uuid_string: str) -> bool:
        """Check if string is valid UUID format."""
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        return bool(re.match(uuid_pattern, uuid_string))

    def validate_uuids(self) -> None:
        """Validate UUIDs in workflow."""
        for node_id, node in self.workflow["nodes"].items():
            if not self.is_valid_uuid(node_id):
                self.error_messages.append(
                    f"Node {node_id} does not have a valid UUID. "
                    f"Run journey_fixes.py to generate valid UUIDs automatically."
                )

            if "id" in node:
                if node["id"] != node_id:
                    self.error_messages.append(
                        f"Node {node_id} has mismatched id field: {node['id']}. "
                        f"Run journey_fixes.py to fix automatically."
                    )
                elif not self.is_valid_uuid(node["id"]):
                    self.error_messages.append(
                        f"The node id for node {node_id} is not a valid UUID: {node['id']}"
                    )
            else:
                self.error_messages.append(
                    f"Node {node_id} is missing 'id' field. "
                    f"Run journey_fixes.py to fix automatically."
                )

        if "head" in self.workflow:
            if not self.is_valid_uuid(self.workflow["head"]):
                self.error_messages.append(
                    f"Workflow head {self.workflow['head']} is not a valid UUID. "
                    f"Run journey_fixes.py to fix automatically."
                )
        else:
            self.error_messages.append("Workflow is missing 'head' field.")

        if "id" in self.workflow:
            if not self.is_valid_uuid(self.workflow["id"]):
                self.error_messages.append(
                    f"Workflow ID is not a valid UUID: {self.workflow['id']}. "
                    f"Run journey_fixes.py to fix automatically."
                )
        else:
            self.error_messages.append(
                "Workflow is missing 'id' field. Run journey_fixes.py to fix automatically."
            )

    def get_node_type(self, node: dict) -> tuple:
        """Get the node type, handling action nodes properly."""
        if "type" in node:
            if node["type"] != "action":
                # Check if this type is marked as an action type in node_defs
                if node["type"] in self.node_defs and self.node_defs[node["type"]].get(
                    "is_action", False
                ):
                    self.error_messages.append(
                        f"Node {node['id']} has an action type: {node['type']} in its type which is not valid."
                    )
                else:
                    return node["type"], self.error_messages
            else:
                if "action" in node:
                    if "type" in node["action"]:
                        if "form" in node["action"]["type"]:
                            if "metadata" in node["action"]:
                                if "type" in node["action"]["metadata"]:
                                    return (
                                        node["action"]["metadata"]["type"],
                                        self.error_messages,
                                    )
                                else:
                                    self.error_messages.append(
                                        f"Node {node['id']} is missing a 'type' key in the 'metadata' key of the 'action' key."
                                    )
                            else:
                                self.error_messages.append(
                                    f"Node {node['id']} is missing a 'metadata' key in the 'action' key."
                                )
                        return node["action"]["type"], self.error_messages
                    else:
                        self.error_messages.append(
                            f"Node {node['id']} is missing a 'type' key in the 'action' key."
                        )
                else:
                    self.error_messages.append(
                        f"Node {node['id']} is missing an 'action' key."
                    )
        else:
            self.error_messages.append(f"Node {node['id']} is missing a 'type' key.")
            return None, self.error_messages

    def validate_node_types(self) -> None:
        """Validate node types."""
        # Invalid action types that must use form structure instead
        INVALID_ACTION_TYPES = ["get_information"]

        for node_id, node in self.workflow["nodes"].items():
            node_type, _ = self.get_node_type(node)
            if node_type:
                # Check if node type is valid (exists in node_definitions.json)
                if node_type not in self.node_defs:
                    self.error_messages.append(
                        f"Node {node_id} has an invalid type: {node_type}."
                    )

                # Check for invalid action types that should use form structure
                if node.get("type") == "action" and "action" in node:
                    action_type = node["action"].get("type")
                    if action_type in INVALID_ACTION_TYPES:
                        self.error_messages.append(
                            f"Node {node_id} uses '{action_type}' as action type, which is invalid. "
                            f"Use form structure instead: "
                            f'{{"type": "form", "metadata": {{"type": "{action_type}"}}, ...}}'
                        )

    def validate_journey_completeness(self) -> None:
        """Validate all nodes are reachable from head."""
        journey_nodes = set(self.workflow["nodes"].keys())
        visited_nodes = set()

        def dfs(node_id: str):
            if node_id in visited_nodes:
                return

            # Check if the node exists
            if node_id not in self.workflow["nodes"]:
                self.error_messages.append(
                    f"Node {node_id} is referenced but does not exist in the journey."
                )
                return

            visited_nodes.add(node_id)
            node = self.workflow["nodes"][node_id]

            if "links" in node:
                for link in node["links"]:
                    if "target" in link and link["target"]:
                        if link["target"] not in visited_nodes:
                            dfs(link["target"])

            if node.get("type") == "block":
                if "block" in node:
                    if "id" in node["block"]:
                        dfs(node["block"]["id"])
                    else:
                        self.error_messages.append(
                            f"Block node {node_id} is missing an 'id' key in the 'block' key."
                        )
                else:
                    self.error_messages.append(
                        f"Block node {node_id} is missing a 'block' key."
                    )

            if node.get("type") == "loop":
                if "loop_body" in node:
                    if "id" in node["loop_body"]:
                        dfs(node["loop_body"]["id"])
                    else:
                        self.error_messages.append(
                            f"Loop node {node_id} is missing an 'id' key in the 'loop_body' key."
                        )
                else:
                    self.error_messages.append(
                        f"Loop node {node_id} is missing a 'loop_body' key."
                    )

        # Check if head exists
        if "head" not in self.workflow:
            self.error_messages.append("Workflow is missing a 'head' field.")
        elif self.workflow["head"] not in self.workflow["nodes"]:
            self.error_messages.append(
                f"Workflow head '{self.workflow['head']}' does not exist in the nodes."
            )
        else:
            dfs(self.workflow["head"])

            # Check for unreachable nodes
            unreachable = journey_nodes - visited_nodes
            if unreachable:
                self._report_unreachable_nodes(unreachable)

    def _report_unreachable_nodes(self, unreachable: Set[str]) -> None:
        """Report unreachable nodes with helpful suggestions."""
        # Find all loop and block nodes to provide helpful suggestions
        loop_and_block_nodes = []
        for node_id, node in self.workflow["nodes"].items():
            if node.get("type") in ["loop", "block"]:
                body_key = "loop_body" if node.get("type") == "loop" else "block"
                referenced_id = None
                if body_key in node and isinstance(node[body_key], dict):
                    referenced_id = node[body_key].get("id")
                loop_and_block_nodes.append(
                    {
                        "id": node_id,
                        "type": node.get("type"),
                        "references": referenced_id,
                    }
                )

        # Sort unreachable nodes for consistent reporting
        unreachable_list = sorted(unreachable)

        for node_id in unreachable_list:
            self.error_messages.append(
                f"Node {node_id} is not reachable from the head node."
            )

        # If there are loop/block nodes, suggest checking their body references
        if loop_and_block_nodes:
            suggestion = (
                f"\n💡 SUGGESTION: Found {len(unreachable_list)} unreachable node(s) and "
                f"{len(loop_and_block_nodes)} loop/block node(s). "
                f"Unreachable nodes are often caused by missing or incorrect loop_body/block references.\n"
            )

            for loop_block in loop_and_block_nodes:
                body_key = "loop_body" if loop_block["type"] == "loop" else "block"
                if loop_block["references"]:
                    suggestion += (
                        f"  • {loop_block['type']} node {loop_block['id']} "
                        f"references {body_key}.id = {loop_block['references']}"
                    )
                    if loop_block["references"] in unreachable_list:
                        suggestion += " ⚠️ (but this node is NOT reachable - check if loop node is reachable)"
                    suggestion += "\n"
                else:
                    suggestion += (
                        f"  • {loop_block['type']} node {loop_block['id']} "
                        f"is missing {body_key}.id reference"
                    )
                    if unreachable_list:
                        suggestion += f" - consider if first unreachable node ({unreachable_list[0]}) should be referenced here"
                    suggestion += "\n"

            suggestion += (
                f"\n  🔧 FIX:\n"
                f"     • Ensure each loop/block node is reachable from the head node\n"
                f"     • Ensure the loop_body/block field contains the full node definition\n"
                f"     • Ensure that same node also exists in the nodes dictionary with matching ID\n"
                f"     • The embedded definition and the dictionary node must be identical"
            )

            self.error_messages.append(suggestion)

    def validate_loop_and_block_body(self) -> None:
        """Validate that loop_body and block definitions match the nodes in the nodes dictionary."""
        for node_id, node in self.workflow["nodes"].items():
            if node["type"] == "block" or node["type"] == "loop":
                body_key = "block" if node["type"] == "block" else "loop_body"
                body = node.get(body_key)

                if body:
                    if "id" in body:
                        body_id = body["id"]
                        body_entry_node = self.workflow["nodes"].get(body_id)

                        if body_entry_node:
                            # The embedded definition must match the node in nodes dict exactly
                            if body_entry_node != body:
                                self.error_messages.append(
                                    f"Node {node_id}: '{body_key}' field does not match node {body_id} in nodes dictionary. "
                                    f"Run journey_fixes.py to synchronize automatically."
                                )
                        else:
                            self.error_messages.append(
                                f"Node {node_id} references node {body_id} in '{body_key}', "
                                f"but that node doesn't exist in the nodes dictionary."
                            )
                    else:
                        self.error_messages.append(
                            f"Node {node_id} is missing an 'id' key in the '{body_key}' field."
                        )
                else:
                    self.error_messages.append(
                        f"Node {node_id} is missing a '{body_key}' field."
                    )

    def validate_loop_references(self) -> None:
        """Validate that nodes don't incorrectly link back to loop/block nodes themselves."""

        def trace_loop_path(loop_id: str, max_nodes: int = 10) -> List[str]:
            """Trace the path through a loop body to show its structure."""
            loop_node = self.workflow["nodes"].get(loop_id)
            if not loop_node:
                return []

            body_key = "loop_body" if loop_node.get("type") == "loop" else "block"
            if body_key not in loop_node or "id" not in loop_node[body_key]:
                return []

            path = []
            current_id = loop_node[body_key]["id"]
            visited = set()

            while (
                current_id
                and current_id in self.workflow["nodes"]
                and len(path) < max_nodes
            ):
                if current_id in visited:
                    path.append(f"{current_id} (cycle detected)")
                    break

                visited.add(current_id)
                path.append(current_id)

                current_node = self.workflow["nodes"][current_id]

                # Follow the first link (usually the main flow)
                if "links" in current_node and len(current_node["links"]) > 0:
                    first_link = current_node["links"][0]
                    current_id = (
                        first_link.get("target") if first_link.get("target") else None
                    )
                else:
                    break

            if len(path) >= max_nodes:
                path.append("...")

            return path

        def collect_body_nodes(body_entry_id: str, visited: set = None) -> set:
            """Collect all nodes that are part of a loop/block body."""
            if visited is None:
                visited = set()

            body_nodes = set()
            to_visit = [body_entry_id]

            while to_visit:
                current_id = to_visit.pop()

                if current_id in visited or current_id not in self.workflow["nodes"]:
                    continue

                visited.add(current_id)
                body_nodes.add(current_id)
                current_node = self.workflow["nodes"][current_id]

                # Follow all links
                if "links" in current_node:
                    for link in current_node["links"]:
                        target = link.get("target")
                        if target and target not in visited:
                            to_visit.append(target)

            return body_nodes

        # Find all loop and block nodes and collect their body nodes
        loop_and_block_nodes = {}
        for node_id, node in self.workflow["nodes"].items():
            if node.get("type") in ["loop", "block"]:
                body_key = "loop_body" if node.get("type") == "loop" else "block"
                if body_key in node and "id" in node[body_key]:
                    body_entry_id = node[body_key]["id"]
                    body_nodes = collect_body_nodes(body_entry_id)
                    loop_and_block_nodes[node_id] = {
                        "type": node["type"],
                        "body_entry_id": body_entry_id,
                        "body_nodes": body_nodes,
                    }

        # Check all nodes for links to loop/block nodes or their first body node
        for node_id, node in self.workflow["nodes"].items():
            if "links" in node:
                for link_idx, link in enumerate(node["links"]):
                    target = link.get("target")
                    if not target:
                        continue

                    # Check if this is a link to a loop/block node itself
                    if target in loop_and_block_nodes:
                        loop_info = loop_and_block_nodes[target]

                        # Check if the linking node is inside this loop's body
                        if node_id not in loop_info["body_nodes"]:
                            # External node linking to loop - this is VALID
                            continue

                        # Node is inside the loop body and linking back to loop node - ERROR
                        loop_path = trace_loop_path(target)
                        path_str = (
                            " → ".join(loop_path) if loop_path else "(unable to trace)"
                        )
                        link_name = link.get("name", f"link[{link_idx}]")

                        self.error_messages.append(
                            f"Node {node_id} has link '{link_name}' that incorrectly targets the {loop_info['type']} "
                            f"node itself ({target}), which creates infinite structural recursion and FREEZES THE EDITOR.\n"
                            f"\n"
                            f"  Loop body nodes: {path_str}\n"
                            f"\n"
                            f'  🔧 FIX: Change the link target to empty/null ("target": null or remove "target" field)\n'
                            f"\n"
                            f"  📖 CRITICAL: IDO loop nodes are CONDITIONAL BRANCH CONTAINERS, not traditional loops:\n"
                            f"  To retry a loop, use links with NO TARGET (null/empty)."
                        )
                        continue

                    # Check if this is a link to the first node of a loop/block body
                    for loop_id, loop_info in loop_and_block_nodes.items():
                        if (
                            target == loop_info["body_entry_id"]
                            and node_id in loop_info["body_nodes"]
                        ):
                            loop_path = trace_loop_path(loop_id)
                            path_str = (
                                " → ".join(loop_path)
                                if loop_path
                                else "(unable to trace)"
                            )
                            link_name = link.get("name", f"link[{link_idx}]")

                            self.error_messages.append(
                                f"Node {node_id} has link '{link_name}' that incorrectly targets the first node "
                                f"in the {loop_info['type']} body ({target}), which creates infinite structural recursion.\n"
                                f"\n"
                                f"  {loop_info['type'].title()} node: {loop_id}\n"
                                f"  Loop body nodes: {path_str}\n"
                                f"\n"
                                f'  🔧 FIX: Change the link target to empty/null ("target": null or remove "target" field)'
                            )
                            break

    def validate_link_structure(self) -> None:
        """Validate that links have required fields and valid structure."""
        valid_link_types = self.constants["valid_link_types"]
        valid_presentation_values = self.constants["valid_presentation_values"]

        for node_id, node in self.workflow["nodes"].items():
            if "links" in node and isinstance(node["links"], list):
                for idx, link in enumerate(node["links"]):
                    if not isinstance(link, dict):
                        self.error_messages.append(
                            f"Node {node_id} link[{idx}] is not a valid object."
                        )
                        continue

                    # Check for required 'type' field
                    if "type" not in link:
                        self.error_messages.append(
                            f"Node {node_id} link[{idx}] is missing required 'type' field. "
                            f"Links must specify a type (e.g., 'branch' or 'escape').\n"
                            f"  Current link: {link}\n"
                            f'  Add: "type": "branch" (or "escape" for error/alternative paths)'
                        )
                    elif link["type"] not in valid_link_types:
                        self.error_messages.append(
                            f"Node {node_id} link[{idx}] has invalid type '{link['type']}'. "
                            f"Valid types are: {', '.join(valid_link_types)}"
                        )

                    # Warn if 'name' is missing
                    if "name" not in link:
                        # Only warn if this isn't a loop retry link
                        if "target" in link and link["target"]:
                            self.error_messages.append(
                                f"Node {node_id} link[{idx}] is missing 'name' field. "
                                f"While not strictly required, links should have descriptive names "
                                f"(e.g., 'success_child', 'failure', 'child')."
                            )

                    # Validate 'presentation' field if present
                    if "presentation" in link:
                        presentation_value = link["presentation"]
                        if presentation_value not in valid_presentation_values:
                            self.error_messages.append(
                                f"Node {node_id} link[{idx}] ('{link.get('name', 'unnamed')}') has invalid presentation value '{presentation_value}'. "
                                f"Must be one of: {', '.join(valid_presentation_values)}"
                            )

    def validate_terminal_nodes(self) -> None:
        """Validate that all outer scope paths terminate in auth_pass or reject nodes."""
        # Get terminal node types from node definitions
        terminal_types = {
            node_type
            for node_type, node_def in self.node_defs.items()
            if node_def.get("is_terminal", False)
        }

        # Identify nodes inside loops/blocks
        loop_and_block_body_nodes = set()
        for node_id, node in self.workflow["nodes"].items():
            if node.get("type") in ["loop", "block"]:
                body_key = "loop_body" if node.get("type") == "loop" else "block"
                if body_key in node and "id" in node[body_key]:
                    body_entry_id = node[body_key]["id"]
                    # Collect all nodes in this loop/block body
                    body_nodes = self._collect_descendant_nodes(body_entry_id)
                    loop_and_block_body_nodes.update(body_nodes)

        # Check all nodes in outer scope for terminal reachability
        for node_id, node in self.workflow["nodes"].items():
            # Skip nodes inside loops/blocks
            if node_id in loop_and_block_body_nodes:
                continue

            # Skip loop and block container nodes themselves
            if node.get("type") in ["loop", "block"]:
                continue

            node_type, _ = self.get_node_type(node)

            # Skip if already a terminal node
            if node_type in terminal_types:
                continue

            # Check if this node has any links
            links = node.get("links", [])

            # Node must have at least one link (unless it's terminal)
            if not links:
                self.error_messages.append(
                    f"❌ Node {node_id} ({node_type}) is in outer scope but has no links and is not a terminal node (auth_pass/reject). "
                    f"All outer scope paths must eventually reach a terminal node."
                )
                continue

            # Check if any link eventually reaches a terminal node
            has_terminal_path = False
            for link in links:
                target = link.get("target")
                if target:
                    if self._path_reaches_terminal(
                        target, loop_and_block_body_nodes, visited=set()
                    ):
                        has_terminal_path = True
                        break

            if not has_terminal_path:
                self.error_messages.append(
                    f"❌ Node {node_id} ({node_type}) is in outer scope but none of its paths reach a terminal node (auth_pass/reject). "
                    f"All outer scope branches must eventually terminate."
                )

    def _collect_descendant_nodes(self, start_node_id: str, visited: set = None) -> set:
        """Collect all nodes reachable from a starting node (for loop/block body detection)."""
        if visited is None:
            visited = set()

        descendants = set()
        to_visit = [start_node_id]

        while to_visit:
            current_id = to_visit.pop()

            if current_id in visited or current_id not in self.workflow["nodes"]:
                continue

            visited.add(current_id)
            descendants.add(current_id)
            current_node = self.workflow["nodes"][current_id]

            # Follow all links
            if "links" in current_node:
                for link in current_node["links"]:
                    target = link.get("target")
                    if target and target not in visited:
                        to_visit.append(target)

        return descendants

    def _path_reaches_terminal(
        self, node_id: str, loop_body_nodes: set, visited: set, max_depth: int = 100
    ) -> bool:
        """Check if a path from node_id eventually reaches a terminal node."""
        # Get terminal node types from node definitions
        terminal_types = {
            node_type
            for node_type, node_def in self.node_defs.items()
            if node_def.get("is_terminal", False)
        }

        if len(visited) > max_depth:
            return False  # Prevent infinite loops

        if node_id in visited or node_id not in self.workflow["nodes"]:
            return False

        visited.add(node_id)
        node = self.workflow["nodes"][node_id]
        node_type, _ = self.get_node_type(node)

        # If we reached a terminal node, success
        if node_type in terminal_types:
            return True

        # If we entered a loop/block from outside, the loop's child link should eventually reach terminal
        if node.get("type") in ["loop", "block"] and node_id not in loop_body_nodes:
            # Check the loop/block's exit links
            links = node.get("links", [])
            for link in links:
                target = link.get("target")
                if target:
                    if self._path_reaches_terminal(
                        target, loop_body_nodes, visited.copy(), max_depth
                    ):
                        return True
            return False

        # For regular nodes, check all outgoing links
        links = node.get("links", [])
        for link in links:
            target = link.get("target")
            if target:
                if self._path_reaches_terminal(
                    target, loop_body_nodes, visited.copy(), max_depth
                ):
                    return True

        return False

    def validate_required_links(self) -> None:
        """Validate that nodes have all their required links based on node type."""
        for node_id, node in self.workflow["nodes"].items():
            node_type, _ = self.get_node_type(node)

            if not node_type:
                continue

            # Special handling for login_form - it uses escape links with auth method names
            if node_type == "login_form":
                # login_form must have at least one escape link with an auth method name
                links = node.get("links", [])
                escape_links = [link for link in links if link.get("type") == "escape"]

                if not escape_links:
                    self.error_messages.append(
                        f"❌ Node {node_id} (login_form) must have at least one escape link for an authentication method. "
                        f"Valid methods: email_otp, native_biometrics, passkeys, password, sms_otp, totp, web_to_mobile"
                    )

                # Ensure no generic "child" branch link
                branch_links = [link for link in links if link.get("type") == "branch"]
                child_links = [
                    link for link in branch_links if link.get("name") == "child"
                ]

                if child_links:
                    self.error_messages.append(
                        f"❌ Node {node_id} (login_form) must NOT use generic 'child' branch links. "
                        f"Use escape links with specific authentication method names instead."
                    )
                continue

            # Check if this node type has required links defined
            if node_type not in self.node_defs:
                continue

            node_def = self.node_defs[node_type]
            required_links_def = node_def.get("required_links", {})

            if not required_links_def:
                continue

            required_branches = required_links_def.get("branch", [])
            required_escapes = required_links_def.get("escape", [])
            links = node.get("links", [])

            # Get actual link names by type
            branch_links = {
                link.get("name")
                for link in links
                if link.get("type") == "branch" and link.get("name")
            }
            escape_links = {
                link.get("name")
                for link in links
                if link.get("type") == "escape" and link.get("name")
            }

            # Check for missing required branch links
            for required_link in required_branches:
                if required_link not in branch_links:
                    # Check if it might be in escape links (common mistake)
                    if required_link in escape_links:
                        self.error_messages.append(
                            f"⚠️  Node {node_id} ({node_type}) has '{required_link}' as escape link, but it should be a branch link."
                        )
                    else:
                        self.error_messages.append(
                            f"❌ Node {node_id} ({node_type}) is missing required branch link: '{required_link}'"
                        )

            # Check for missing required escape links
            for required_link in required_escapes:
                if required_link not in escape_links:
                    # Check if it might be in branch links (common mistake)
                    if required_link in branch_links:
                        self.error_messages.append(
                            f"⚠️  Node {node_id} ({node_type}) has '{required_link}' as branch link, but it should be an escape link."
                        )
                    else:
                        self.error_messages.append(
                            f"❌ Node {node_id} ({node_type}) is missing required escape link: '{required_link}'"
                        )


if __name__ == "__main__":
    JourneyStructureValidator.main()
