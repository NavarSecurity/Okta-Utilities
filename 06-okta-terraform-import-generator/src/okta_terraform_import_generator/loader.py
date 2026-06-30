from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from .utils import read_json, listify


class BackupLoader:
    def __init__(self, backup_dir: Path):
        self.backup_dir = backup_dir

    def exists(self, filename: str) -> bool:
        return (self.backup_dir / filename).exists()

    def load(self, filename: str) -> Any:
        return read_json(self.backup_dir / filename)

    def load_list_file(self, filename: str) -> List[Dict[str, Any]]:
        path = self.backup_dir / filename
        if not path.exists():
            return []
        data = read_json(path)
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [data]
        return []

    def groups(self) -> List[Dict[str, Any]]:
        return self.load_list_file("groups.json")

    def applications(self) -> List[Dict[str, Any]]:
        return self.load_list_file("applications.json")

    def trusted_origins(self) -> List[Dict[str, Any]]:
        return self.load_list_file("trusted_origins.json")

    def network_zones(self) -> List[Dict[str, Any]]:
        return self.load_list_file("network_zones.json")

    def identity_providers(self) -> List[Dict[str, Any]]:
        return self.load_list_file("identity_providers.json")

    def domains(self) -> List[Dict[str, Any]]:
        path = self.backup_dir / "domains.json"
        if not path.exists():
            return []
        data = read_json(path)
        if isinstance(data, dict) and isinstance(data.get("domains"), list):
            return [x for x in data["domains"] if isinstance(x, dict)]
        if isinstance(data, list):
            out: List[Dict[str, Any]] = []
            for item in data:
                if isinstance(item, dict) and isinstance(item.get("domains"), list):
                    out.extend([x for x in item["domains"] if isinstance(x, dict)])
                elif isinstance(item, dict):
                    out.append(item)
            return out
        return []

    def authorization_server_bundle(self) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
        path = self.backup_dir / "authorization_servers.json"
        if not path.exists():
            return [], {}
        data = read_json(path)
        servers: List[Dict[str, Any]] = []
        details: Dict[str, Dict[str, Any]] = {}
        records = listify(data)
        for item in records:
            if isinstance(item, dict):
                if isinstance(item.get("authorizationServers"), list):
                    servers.extend([x for x in item["authorizationServers"] if isinstance(x, dict)])
                elif "id" in item and ("audiences" in item or "issuer" in item or "name" in item):
                    servers.append(item)
                if isinstance(item.get("detailsByAuthorizationServerId"), dict):
                    for k, v in item["detailsByAuthorizationServerId"].items():
                        if isinstance(v, dict):
                            details[k] = v
        return servers, details

    def policies(self) -> List[Dict[str, Any]]:
        path = self.backup_dir / "policies.json"
        if not path.exists():
            return []
        data = read_json(path)
        policies: List[Dict[str, Any]] = []
        if isinstance(data, dict) and isinstance(data.get("policyTypes"), dict):
            for policy_type, record in data["policyTypes"].items():
                if isinstance(record, dict) and isinstance(record.get("policies"), list):
                    for p in record["policies"]:
                        if isinstance(p, dict):
                            p = dict(p)
                            p.setdefault("type", policy_type)
                            policies.append(p)
        elif isinstance(data, list):
            policies = [x for x in data if isinstance(x, dict)]
        return policies
