"""Report Generator - Auto-Generate Client Reports (Phase 10 Week 2)"""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from .utils import DATA_DIR, log, log_error
from .clients import client_manager
from .broadcast_history import broadcast_history

REPORTS_DIR = DATA_DIR / "reports"

class ReportGenerator:
    """Auto-generate professional reports for clients"""
    
    def __init__(self):
        self.reports_dir = REPORTS_DIR
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_report(self, client_id: str, format: str = "txt", 
                        date_range: str = "today") -> Optional[str]:
        """Generate report for a client"""
        
        client = client_manager.get_client(client_id)
        if not client:
            log_error(f"Client not found: {client_id}")
            return None
        
        # Get date range
        if date_range == "today":
            start_date = datetime.now().date()
            end_date = datetime.now().date()
        elif date_range == "week":
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)
        elif date_range == "month":
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date = datetime.now().date()
        
        # Get stats
        stats = client_manager.get_client_stats(client_id)
        limits_check = client_manager.check_limits(client_id)
        
        # Generate content based on format
        if format == "txt":
            content = self._generate_txt_report(client, stats, limits_check, start_date, end_date)
            ext = ".txt"
        elif format == "csv":
            content = self._generate_csv_report(client_id, start_date, end_date)
            ext = ".csv"
        elif format == "json":
            content = self._generate_json_report(client, stats, limits_check, start_date, end_date)
            ext = ".json"
        else:
            log_error(f"Unsupported format: {format}")
            return None
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"report_{client_id}_{date_range}_{timestamp}{ext}"
        filepath = self.reports_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        log(f"Report generated: {filename}", "success")
        return str(filepath)
    
    def _generate_txt_report(self, client, stats, limits_check, start_date, end_date) -> str:
        """Generate text format report"""
        return f"""
═══════════════════════════════════════
       BROADCAST REPORT - {client['name']}
═══════════════════════════════════════

Period: {start_date} to {end_date}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tier: {client['tier'].upper()}

───────────────────────────────────────
STATISTICS
───────────────────────────────────────
Total Broadcasts: {stats['total_broadcasts']}
Total Sent: {stats['total_sent']}
Total Failed: {stats['total_failed']}
Success Rate: {stats['avg_success_rate']}%
Messages Today: {stats['messages_today']}

───────────────────────────────────────
USAGE vs LIMITS
───────────────────────────────────────
{limits_check.get('usage', {})}

───────────────────────────────────────
RECOMMENDATIONS
───────────────────────────────────────
{self._generate_recommendations(stats, limits_check)}

═══════════════════════════════════════
Thank you for using TG PRO QUANTUM!
═══════════════════════════════════════
        """.strip()
    
    def _generate_csv_report(self, client_id: str, start_date, end_date) -> str:
        """Generate CSV format report"""
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Client Report", client_manager.get_client(client_id)['name']])
        writer.writerow(["Period", f"{start_date} to {end_date}"])
        writer.writerow(["Generated", datetime.now().isoformat()])
        writer.writerow([])
        
        # Stats header
        writer.writerow(["Metric", "Value"])
        stats = client_manager.get_client_stats(client_id)
        for key, value in stats.items():
            writer.writerow([key, value])
        
        return output.getvalue()
    
    def _generate_json_report(self, client, stats, limits_check, start_date, end_date) -> str:
        """Generate JSON format report"""
        report = {
            "client": {
                "id": client["id"],
                "name": client["name"],
                "email": client["email"],
                "tier": client["tier"]
            },
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "generated_at": datetime.now().isoformat(),
            "stats": stats,
            "limits": limits_check,
            "recommendations": self._generate_recommendations(stats, limits_check)
        }
        return json.dumps(report, indent=2, ensure_ascii=False)
    
    def _generate_recommendations(self, stats, limits_check) -> str:
        """Generate recommendations based on stats"""
        recommendations = []
        
        if stats.get('avg_success_rate', 100) < 90:
            recommendations.append("• Success rate below 90% - Review account quality")
        
        if not limits_check.get('checks', {}).get('messages', True):
            recommendations.append("• Approaching message limit - Consider upgrading tier")
        
        if stats.get('total_broadcasts', 0) == 0:
            recommendations.append("• No broadcasts yet - Start your first campaign!")
        
        if not recommendations:
            recommendations.append("• All metrics look good! Keep up the great work! 🎉")
        
        return "\n".join(recommendations)
    
    def auto_generate_reports(self):
        """Auto-generate reports for clients with auto_reports enabled"""
        generated = []
        
        for client in client_manager.get_all_clients():
            settings = client.get("settings", {})
            if settings.get("auto_reports", False):
                frequency = settings.get("report_frequency", "weekly")
                
                # Generate report
                filepath = self.generate_report(
                    client_id=client["id"],
                    format="txt",
                    date_range=frequency
                )
                
                if filepath:
                    generated.append(filepath)
                    log(f"Auto-report generated for {client['name']}: {filepath}", "info")
        
        return generated


# Global instance
report_generator = ReportGenerator()
__all__ = ["ReportGenerator", "report_generator"]