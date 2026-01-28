# src/radiology_reports/utils/config.py
"""
Smart config that works on your laptop AND in production — zero crashes.
"""

import os
import socket
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
BASE_DIR = Path(__file__).resolve().parents[3]
load_dotenv(BASE_DIR / ".env")


class Config:
    DB_DRIVER = os.getenv("DB_DRIVER", "{ODBC Driver 17 for SQL Server}")
    DB_DATABASE = os.getenv("DB_DATABASE", "RRC_Daily_Report")
    DB_TRUSTED_CONNECTION = os.getenv("DB_TRUSTED_CONNECTION", "yes")

    # These might be missing → provide safe defaults
    DB_SERVER_PROD = os.getenv("DB_SERVER_PROD", "phiSQL1.rrc.center").strip()
    DB_SERVER_LOCAL = os.getenv("DB_SERVER_LOCAL", "DESKTOP-FLC2FFF\\MSSQLSERVER01").strip()

    SMTP_SERVER = os.getenv("SMTP_SERVER", "phimlr1.rrc.center")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "dparrish@radiologyregional.com")
    DEFAULT_RECIPIENTS = [
        e.strip() for e in os.getenv("DEFAULT_RECIPIENTS", "dparrish@radiologyregional.com").split(",")
        if e.strip()
    ]
    
    # NEW — OPS-only recipients
    OPS_RECIPIENTS = [
        e.strip()
        for e in os.getenv("OPS_RECIPIENTS", "").split(",")
        if e.strip()
    ]

    def _can_connect_to(self, server: str, timeout: float = 1.5) -> bool:
        """Fast TCP check on port 1433 (SQL Server default)"""
        if not server:
            return False
        try:
            host = server.split("\\")[0].split(":")[0]  # extract hostname only
            socket.setdefaulttimeout(timeout)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, 1433))
            return True
        except (socket.timeout, socket.gaierror, OSError, Exception):
            return False

    @property
    def DB_SERVER(self) -> str:
        """Auto-pick the reachable server"""
        if self.DB_SERVER_PROD and self._can_connect_to(self.DB_SERVER_PROD):
            print(f"Connected to PRODUCTION server: {self.DB_SERVER_PROD}")
            return self.DB_SERVER_PROD
        else:
            print(f"Using LOCAL server: {self.DB_SERVER_LOCAL}")
            return self.DB_SERVER_LOCAL

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"DRIVER={self.DB_DRIVER};"
            f"SERVER=" + self.DB_SERVER + ";"
            f"DATABASE={self.DB_DATABASE};"
            f"Trusted_Connection={self.DB_TRUSTED_CONNECTION};"
        )

    def __repr__(self):
        return f"<Config server={self.DB_SERVER} db={self.DB_DATABASE}>"


# Singleton
config = Config()