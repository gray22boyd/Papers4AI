"""
Sourcing Campaign Manager
Manages recruiting campaigns with Kanban-style pipeline tracking
"""
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

# Default pipeline stages
DEFAULT_STAGES = [
    {"id": "new", "name": "New Leads", "color": "#6B7280"},
    {"id": "contacted", "name": "Contacted", "color": "#3B82F6"},
    {"id": "follow_up", "name": "Follow Up", "color": "#F59E0B"},
]


class CampaignManager:
    """Manages sourcing campaigns for users"""

    def __init__(self, data_file: Path):
        self.data_file = data_file
        self.campaigns = self._load_campaigns()

    def _load_campaigns(self) -> Dict:
        """Load campaigns from JSON file"""
        if self.data_file.exists():
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CAMPAIGN] Error loading campaigns: {e}")
                return {}
        return {}

    def _save_campaigns(self):
        """Save campaigns to JSON file"""
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.campaigns, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[CAMPAIGN] Error saving campaigns: {e}")
            raise

    # ========================================================================
    # Campaign Management
    # ========================================================================

    def create_campaign(
        self,
        user_id: str,
        name: str,
        description: str = "",
        stages: List[Dict] = None
    ) -> Dict:
        """
        Create a new recruiting campaign

        Args:
            user_id: User who owns the campaign
            name: Campaign name
            description: Campaign description
            stages: Custom pipeline stages (defaults to DEFAULT_STAGES)

        Returns:
            Created campaign dict
        """
        campaign_id = str(uuid.uuid4())

        campaign = {
            "id": campaign_id,
            "user_id": user_id,
            "name": name,
            "description": description,
            "stages": stages or DEFAULT_STAGES.copy(),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "candidates": {},  # candidate_id -> candidate_data
            "archived": False
        }

        # Store under user's campaigns
        if user_id not in self.campaigns:
            self.campaigns[user_id] = {}

        self.campaigns[user_id][campaign_id] = campaign
        self._save_campaigns()

        return campaign

    def get_user_campaigns(self, user_id: str, include_archived: bool = False) -> List[Dict]:
        """
        Get all campaigns for a user

        Args:
            user_id: User ID
            include_archived: Include archived campaigns

        Returns:
            List of campaign dicts
        """
        if user_id not in self.campaigns:
            return []

        campaigns = list(self.campaigns[user_id].values())

        if not include_archived:
            campaigns = [c for c in campaigns if not c.get("archived", False)]

        # Sort by updated_at descending
        campaigns.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return campaigns

    def get_campaign(self, user_id: str, campaign_id: str) -> Optional[Dict]:
        """Get a specific campaign"""
        if user_id not in self.campaigns:
            return None
        return self.campaigns[user_id].get(campaign_id)

    def update_campaign(
        self,
        user_id: str,
        campaign_id: str,
        name: str = None,
        description: str = None,
        stages: List[Dict] = None,
        archived: bool = None
    ) -> Optional[Dict]:
        """Update campaign metadata"""
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign:
            return None

        if name is not None:
            campaign["name"] = name
        if description is not None:
            campaign["description"] = description
        if stages is not None:
            campaign["stages"] = stages
        if archived is not None:
            campaign["archived"] = archived

        campaign["updated_at"] = datetime.now().isoformat()

        self._save_campaigns()
        return campaign

    def delete_campaign(self, user_id: str, campaign_id: str) -> bool:
        """Delete a campaign"""
        if user_id not in self.campaigns:
            return False
        if campaign_id not in self.campaigns[user_id]:
            return False

        del self.campaigns[user_id][campaign_id]
        self._save_campaigns()
        return True

    # ========================================================================
    # Candidate Management
    # ========================================================================

    def add_candidate(
        self,
        user_id: str,
        campaign_id: str,
        candidate_data: Dict,
        stage_id: str = "new"
    ) -> Optional[Dict]:
        """
        Add a candidate to a campaign

        Args:
            user_id: User ID
            campaign_id: Campaign ID
            candidate_data: Candidate info (from search results)
            stage_id: Initial stage (default: "new")

        Returns:
            Updated campaign dict
        """
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign:
            return None

        # Generate candidate ID from name (or use existing ID)
        candidate_id = candidate_data.get("id") or str(uuid.uuid4())

        # Create campaign candidate entry
        campaign_candidate = {
            "id": candidate_id,
            "candidate_data": candidate_data,
            "stage_id": stage_id,
            "added_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tasks": [],
            "notes": [],
            "timeline": [
                {
                    "timestamp": datetime.now().isoformat(),
                    "event": "added_to_campaign",
                    "stage_id": stage_id,
                    "description": f"Added to campaign at stage: {stage_id}"
                }
            ]
        }

        campaign["candidates"][candidate_id] = campaign_candidate
        campaign["updated_at"] = datetime.now().isoformat()

        self._save_campaigns()
        return campaign

    def move_candidate(
        self,
        user_id: str,
        campaign_id: str,
        candidate_id: str,
        new_stage_id: str
    ) -> Optional[Dict]:
        """
        Move candidate to a different stage (drag-and-drop)

        Args:
            user_id: User ID
            campaign_id: Campaign ID
            candidate_id: Candidate ID
            new_stage_id: Target stage ID

        Returns:
            Updated campaign dict
        """
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign:
            return None

        if candidate_id not in campaign["candidates"]:
            return None

        candidate = campaign["candidates"][candidate_id]
        old_stage_id = candidate["stage_id"]

        # Update stage
        candidate["stage_id"] = new_stage_id
        candidate["updated_at"] = datetime.now().isoformat()

        # Add timeline event
        candidate["timeline"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "stage_changed",
            "old_stage_id": old_stage_id,
            "new_stage_id": new_stage_id,
            "description": f"Moved from {old_stage_id} to {new_stage_id}"
        })

        campaign["updated_at"] = datetime.now().isoformat()

        self._save_campaigns()
        return campaign

    def remove_candidate(
        self,
        user_id: str,
        campaign_id: str,
        candidate_id: str
    ) -> Optional[Dict]:
        """Remove a candidate from a campaign"""
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign:
            return None

        if candidate_id in campaign["candidates"]:
            del campaign["candidates"][candidate_id]
            campaign["updated_at"] = datetime.now().isoformat()
            self._save_campaigns()

        return campaign

    # ========================================================================
    # Task Management
    # ========================================================================

    def add_task(
        self,
        user_id: str,
        campaign_id: str,
        candidate_id: str,
        task_type: str,
        description: str,
        due_date: str = None,
        completed: bool = False
    ) -> Optional[Dict]:
        """
        Add a task for a candidate

        Args:
            user_id: User ID
            campaign_id: Campaign ID
            candidate_id: Candidate ID
            task_type: Type of task (e.g., "email", "follow_up", "call", "note")
            description: Task description
            due_date: ISO format due date (optional)
            completed: Whether task is completed

        Returns:
            Updated campaign dict
        """
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign:
            return None

        if candidate_id not in campaign["candidates"]:
            return None

        task_id = str(uuid.uuid4())
        task = {
            "id": task_id,
            "type": task_type,
            "description": description,
            "due_date": due_date,
            "completed": completed,
            "created_at": datetime.now().isoformat(),
            "completed_at": datetime.now().isoformat() if completed else None
        }

        candidate = campaign["candidates"][candidate_id]
        candidate["tasks"].append(task)
        candidate["updated_at"] = datetime.now().isoformat()

        # Add timeline event
        candidate["timeline"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "task_added",
            "task_type": task_type,
            "description": f"Task added: {description}"
        })

        campaign["updated_at"] = datetime.now().isoformat()

        self._save_campaigns()
        return campaign

    def update_task(
        self,
        user_id: str,
        campaign_id: str,
        candidate_id: str,
        task_id: str,
        completed: bool = None,
        description: str = None,
        due_date: str = None
    ) -> Optional[Dict]:
        """Update a task"""
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign:
            return None

        if candidate_id not in campaign["candidates"]:
            return None

        candidate = campaign["candidates"][candidate_id]
        task = next((t for t in candidate["tasks"] if t["id"] == task_id), None)

        if not task:
            return None

        if completed is not None:
            task["completed"] = completed
            task["completed_at"] = datetime.now().isoformat() if completed else None

        if description is not None:
            task["description"] = description

        if due_date is not None:
            task["due_date"] = due_date

        candidate["updated_at"] = datetime.now().isoformat()
        campaign["updated_at"] = datetime.now().isoformat()

        self._save_campaigns()
        return campaign

    def add_note(
        self,
        user_id: str,
        campaign_id: str,
        candidate_id: str,
        note: str
    ) -> Optional[Dict]:
        """Add a note to a candidate"""
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign:
            return None

        if candidate_id not in campaign["candidates"]:
            return None

        note_entry = {
            "id": str(uuid.uuid4()),
            "note": note,
            "created_at": datetime.now().isoformat()
        }

        candidate = campaign["candidates"][candidate_id]
        candidate["notes"].append(note_entry)
        candidate["updated_at"] = datetime.now().isoformat()

        # Add timeline event
        candidate["timeline"].append({
            "timestamp": datetime.now().isoformat(),
            "event": "note_added",
            "description": f"Note added: {note[:50]}..."
        })

        campaign["updated_at"] = datetime.now().isoformat()

        self._save_campaigns()
        return campaign

    # ========================================================================
    # Statistics
    # ========================================================================

    def get_campaign_stats(self, user_id: str, campaign_id: str) -> Optional[Dict]:
        """Get statistics for a campaign"""
        campaign = self.get_campaign(user_id, campaign_id)
        if not campaign:
            return None

        candidates = campaign["candidates"]
        total_candidates = len(candidates)

        # Count by stage
        stage_counts = {}
        for stage in campaign["stages"]:
            stage_id = stage["id"]
            count = sum(1 for c in candidates.values() if c["stage_id"] == stage_id)
            stage_counts[stage_id] = count

        # Count tasks
        total_tasks = sum(len(c["tasks"]) for c in candidates.values())
        completed_tasks = sum(
            sum(1 for t in c["tasks"] if t["completed"])
            for c in candidates.values()
        )

        # Overdue tasks
        now = datetime.now()
        overdue_tasks = 0
        for candidate in candidates.values():
            for task in candidate["tasks"]:
                if not task["completed"] and task.get("due_date"):
                    try:
                        due = datetime.fromisoformat(task["due_date"])
                        if due < now:
                            overdue_tasks += 1
                    except:
                        pass

        return {
            "total_candidates": total_candidates,
            "stage_counts": stage_counts,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "overdue_tasks": overdue_tasks,
            "completion_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        }


# Global instance (initialized in app.py)
campaign_manager = None


def initialize(data_file: Path):
    """Initialize the campaign manager"""
    global campaign_manager
    campaign_manager = CampaignManager(data_file)
    return campaign_manager
