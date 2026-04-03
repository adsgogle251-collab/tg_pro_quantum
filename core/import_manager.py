"""TG PRO QUANTUM - Complete Import Manager
Support: Sessions, Phones, Accounts, Groups
"""
import csv
import json
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from .utils import DATA_DIR, SESSIONS_DIR, log, log_error, log_success
from .account_manager import account_manager

IMPORT_LOG_FILE = DATA_DIR / "import_log.json"

@dataclass
class ImportResult:
    success: bool
    import_type: str
    total_processed: int = 0
    imported: int = 0
    skipped: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    imported_items: List[Dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "import_type": self.import_type,
            "total_processed": self.total_processed,
            "imported": self.imported,
            "skipped": self.skipped,
            "failed": self.failed,
            "errors": self.errors[:10],  # Limit errors
            "warnings": self.warnings[:10],
            "timestamp": self.timestamp
        }

class ImportValidator:
    """Validate import data"""
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """Validate phone number format"""
        phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        if not phone.startswith('+'):
            return False, "Phone must start with country code (+)"
        
        digits = re.sub(r'[^\d]', '', phone)
        if len(digits) < 10:
            return False, "Phone number too short"
        if len(digits) > 15:
            return False, "Phone number too long"
        
        return True, phone
    
    @staticmethod
    def validate_session_file(filepath: Path) -> Tuple[bool, str]:
        """Validate Telegram session file"""
        if not filepath.exists():
            return False, "File not found"
        
        if filepath.suffix not in ['.session', '.session-journal']:
            return False, "Invalid file extension (must be .session)"
        
        if filepath.stat().st_size < 100:
            return False, "File too small to be valid session"
        
        return True, str(filepath)
    
    @staticmethod
    def validate_csv_format(filepath: Path, required_columns: List[str]) -> Tuple[bool, str]:
        """Validate CSV file format"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    return False, "Empty CSV file"
                
                missing = set(required_columns) - set(reader.fieldnames)
                if missing:
                    return False, f"Missing columns: {missing}"
                
                return True, "Valid"
        except Exception as e:
            return False, f"CSV read error: {e}"

class ImportManager:
    """Complete Import Manager for Commercial Use"""
    
    def __init__(self):
        self.import_log_file = IMPORT_LOG_FILE
        self.validator = ImportValidator()
        self._import_history: List[Dict] = []
        self._load_history()
    
    def _load_history(self):
        """Load import history"""
        if self.import_log_file.exists():
            try:
                with open(self.import_log_file, 'r', encoding='utf-8') as f:
                    self._import_history = json.load(f)
            except:
                self._import_history = []
    
    def _save_history(self):
        """Save import history"""
        try:
            self.import_log_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.import_log_file, 'w', encoding='utf-8') as f:
                json.dump(self._import_history[-100:], f, indent=2)
        except:
            pass
    
    def _log_import(self, result: ImportResult):
        """Log import operation"""
        self._import_history.append(result.to_dict())
        self._save_history()
    
    # ==================== SESSION IMPORT ====================
    
    def import_session_single(self, filepath: str, account_name: Optional[str] = None) -> ImportResult:
        """Import single session file"""
        result = ImportResult(success=False, import_type="session_single")
        filepath = Path(filepath)
        
        valid, msg = self.validator.validate_session_file(filepath)
        if not valid:
            result.errors.append(msg)
            return result
        
        result.total_processed = 1
        
        # Determine account name
        if account_name:
            name = account_name
        else:
            name = filepath.stem.replace('.session', '')
        
        # Copy to sessions folder
        target = SESSIONS_DIR / f"{name}.session"
        if target.exists():
            result.skipped += 1
            result.warnings.append(f"Session '{name}' already exists")
            return result
        
        try:
            shutil.copy2(filepath, target)
            result.imported = 1
            result.imported_items.append({"name": name, "source": str(filepath), "type": "session"})
            
            # Add to account manager
            if not any(a['name'] == name for a in account_manager.get_all()):
                account_manager.add(name, f"+62{name[-8:]}", level=1)
            
            result.success = True
            log_success(f"Session imported: {name}")
            
        except Exception as e:
            result.failed += 1
            result.errors.append(f"Copy failed: {str(e)}")
            log_error(f"Session import failed: {e}")
        
        self._log_import(result)
        return result
    
    def import_sessions_folder(self, folder: str, recursive: bool = True, auto_categorize: bool = True) -> ImportResult:
        """Import multiple session files from folder"""
        result = ImportResult(success=False, import_type="sessions_folder")
        folder = Path(folder)
        
        if not folder.exists() or not folder.is_dir():
            result.errors.append(f"Folder not found: {folder}")
            return result
        
        # Find session files
        if recursive:
            session_files = list(folder.rglob('*.session'))
        else:
            session_files = list(folder.glob('*.session'))
        
        result.total_processed = len(session_files)
        
        for session_file in session_files:
            valid, msg = self.validator.validate_session_file(session_file)
            if not valid:
                result.skipped += 1
                result.warnings.append(f"{session_file.name}: {msg}")
                continue
            
            # Extract account name from filename
            account_name = session_file.stem.replace('.session', '')
            
            # Auto-categorize based on filename patterns
            if auto_categorize:
                assigned_feature = None
                if 'finder' in account_name.lower():
                    assigned_feature = "finder"
                elif 'scrape' in account_name.lower():
                    assigned_feature = "scrape"
                elif 'join' in account_name.lower():
                    assigned_feature = "join"
                elif 'broadcast' in account_name.lower():
                    assigned_feature = "broadcast"
                elif 'cs' in account_name.lower() or 'csystem' in account_name.lower():
                    assigned_feature = "cs"
            
            # Copy to sessions folder
            target = SESSIONS_DIR / f"{account_name}.session"
            if not target.exists():
                try:
                    shutil.copy2(session_file, target)
                    result.imported += 1
                    result.imported_items.append({
                        "name": account_name,
                        "source": str(session_file),
                        "type": "session"
                    })
                    
                    # Add to account manager
                    if not any(a['name'] == account_name for a in account_manager.get_all()):
                        account_manager.add(account_name, f"+62{account_name[-8:]}", level=1)
                    
                except Exception as e:
                    result.failed += 1
                    result.errors.append(f"{account_name}: {str(e)}")
            else:
                result.skipped += 1
                result.warnings.append(f"{account_name}: Already exists")
        
        result.success = result.imported > 0
        self._log_import(result)
        log_success(f"Imported {result.imported}/{result.total_processed} sessions")
        return result
    
    # ==================== PHONE IMPORT ====================
    
    def import_phones_csv(self, filepath: str, delimiter: str = ',', name_col: str = 'name', 
                          phone_col: str = 'phone', level_col: str = 'level') -> ImportResult:
        """Import phone numbers from CSV"""
        result = ImportResult(success=False, import_type="phones_csv")
        filepath = Path(filepath)
        
        valid, msg = self.validator.validate_csv_format(filepath, [name_col, phone_col])
        if not valid:
            result.errors.append(msg)
            return result
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=2):
                    result.total_processed += 1
                    
                    name = row.get(name_col, '').strip()
                    phone = row.get(phone_col, '').strip()
                    level = int(row.get(level_col, '1'))
                    
                    if not name or not phone:
                        result.skipped += 1
                        result.warnings.append(f"Row {row_num}: Missing name or phone")
                        continue
                    
                    valid_phone, phone_msg = self.validator.validate_phone(phone)
                    if not valid_phone:
                        result.skipped += 1
                        result.errors.append(f"Row {row_num}: {phone_msg}")
                        continue
                    
                    if any(a['name'] == name for a in account_manager.get_all()):
                        result.skipped += 1
                        result.warnings.append(f"Row {row_num}: Account '{name}' already exists")
                        continue
                    
                    if account_manager.add(name, phone, level):
                        result.imported += 1
                        result.imported_items.append({
                            "name": name,
                            "phone": phone,
                            "level": level,
                            "type": "phone"
                        })
                    else:
                        result.skipped += 1
                        result.errors.append(f"Row {row_num}: Failed to add account")
            
            result.success = result.imported > 0
            self._log_import(result)
            log_success(f"Imported {result.imported}/{result.total_processed} phones from CSV")
            
        except Exception as e:
            result.errors.append(f"Import error: {str(e)}")
            log_error(f"CSV import failed: {e}")
        
        return result
    
    def import_phones_txt(self, filepath: str, format: str = 'pipe') -> ImportResult:
        """Import phone numbers from TXT (name|phone|level format)"""
        result = ImportResult(success=False, import_type="phones_txt")
        filepath = Path(filepath)
        
        if not filepath.exists():
            result.errors.append("File not found")
            return result
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    result.total_processed += 1
                    line = line.strip()
                    
                    if not line or line.startswith('#'):
                        result.skipped += 1
                        continue
                    
                    # Parse based on format
                    if format == 'pipe':
                        parts = line.split('|')
                    elif format == 'comma':
                        parts = line.split(',')
                    elif format == 'tab':
                        parts = line.split('\t')
                    else:
                        parts = line.split('|')
                    
                    if len(parts) < 2:
                        result.skipped += 1
                        result.warnings.append(f"Line {line_num}: Invalid format (expected: name|phone|level)")
                        continue
                    
                    name = parts[0].strip()
                    phone = parts[1].strip()
                    level = int(parts[2].strip()) if len(parts) > 2 else 1
                    
                    valid_phone, phone_msg = self.validator.validate_phone(phone)
                    if not valid_phone:
                        result.skipped += 1
                        result.errors.append(f"Line {line_num}: {phone_msg}")
                        continue
                    
                    if any(a['name'] == name for a in account_manager.get_all()):
                        result.skipped += 1
                        continue
                    
                    if account_manager.add(name, phone, level):
                        result.imported += 1
                        result.imported_items.append({
                            "name": name,
                            "phone": phone,
                            "type": "phone"
                        })
            
            result.success = result.imported > 0
            self._log_import(result)
            log_success(f"Imported {result.imported}/{result.total_processed} phones from TXT")
            
        except Exception as e:
            result.errors.append(f"Import error: {str(e)}")
            log_error(f"TXT import failed: {e}")
        
        return result
    
    def import_phones_excel(self, filepath: str, sheet_name: Optional[str] = None) -> ImportResult:
        """Import phone numbers from Excel"""
        result = ImportResult(success=False, import_type="phones_excel")
        filepath = Path(filepath)
        
        if not filepath.exists():
            result.errors.append("File not found")
            return result
        
        try:
            import openpyxl
            wb = openpyxl.load_workbook(filepath)
            sheet = wb[sheet_name] if sheet_name else wb.active
            
            headers = [cell.value for cell in sheet[1]]
            name_idx = headers.index('name') if 'name' in headers else 0
            phone_idx = headers.index('phone') if 'phone' in headers else 1
            level_idx = headers.index('level') if 'level' in headers else 2
            
            for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                result.total_processed += 1
                
                name = str(row[name_idx]).strip() if row[name_idx] else ''
                phone = str(row[phone_idx]).strip() if row[phone_idx] else ''
                level = int(row[level_idx]) if row[level_idx] else 1
                
                if not name or not phone:
                    result.skipped += 1
                    continue
                
                valid_phone, phone_msg = self.validator.validate_phone(phone)
                if not valid_phone:
                    result.skipped += 1
                    result.errors.append(f"Row {row_num}: {phone_msg}")
                    continue
                
                if any(a['name'] == name for a in account_manager.get_all()):
                    result.skipped += 1
                    continue
                
                if account_manager.add(name, phone, level):
                    result.imported += 1
                    result.imported_items.append({
                        "name": name,
                        "phone": phone,
                        "level": level,
                        "type": "phone"
                    })
            
            result.success = result.imported > 0
            self._log_import(result)
            log_success(f"Imported {result.imported}/{result.total_processed} phones from Excel")
            
        except ImportError:
            result.errors.append("openpyxl not installed. Run: pip install openpyxl")
        except Exception as e:
            result.errors.append(f"Import error: {str(e)}")
            log_error(f"Excel import failed: {e}")
        
        return result
    
    # ==================== GROUP IMPORT ====================
    
    def import_groups(self, filepath: str, validate: bool = True) -> ImportResult:
        """Import groups from file (one link per line)"""
        result = ImportResult(success=False, import_type="groups")
        filepath = Path(filepath)
        
        if not filepath.exists():
            result.errors.append("File not found")
            return result
        
        from .utils import save_group, load_groups
        existing = set(load_groups())
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, start=1):
                    result.total_processed += 1
                    group = line.strip()
                    
                    if not group or group.startswith('#'):
                        result.skipped += 1
                        continue
                    
                    if validate and not group.startswith(('https://t.me/', 't.me/')):
                        result.skipped += 1
                        result.warnings.append(f"Line {line_num}: Invalid group format")
                        continue
                    
                    if group in existing:
                        result.skipped += 1
                        continue
                    
                    save_group(group)
                    existing.add(group)
                    result.imported += 1
                    result.imported_items.append({"group": group, "type": "group"})
            
            result.success = result.imported > 0
            self._log_import(result)
            log_success(f"Imported {result.imported}/{result.total_processed} groups")
            
        except Exception as e:
            result.errors.append(f"Import error: {str(e)}")
            log_error(f"Group import failed: {e}")
        
        return result
    
    # ==================== BATCH IMPORT ====================
    
    def batch_import(self, imports: List[Dict]) -> Dict[str, ImportResult]:
        """Process multiple imports in batch"""
        results = {}
        
        for imp in imports:
            imp_type = imp.get("type")
            filepath = imp.get("filepath")
            
            if not imp_type or not filepath:
                continue
            
            if imp_type == "phones_csv":
                results["phones_csv"] = self.import_phones_csv(filepath)
            elif imp_type == "phones_txt":
                results["phones_txt"] = self.import_phones_txt(filepath)
            elif imp_type == "phones_excel":
                results["phones_excel"] = self.import_phones_excel(filepath)
            elif imp_type == "sessions":
                results["sessions"] = self.import_sessions_folder(filepath)
            elif imp_type == "groups":
                results["groups"] = self.import_groups(filepath)
        
        return results
    
    # ==================== EXPORT ====================
    
    def export_accounts(self, filepath: str, format: str = 'csv') -> bool:
        """Export accounts to file"""
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            accounts = account_manager.get_all()
            
            if format == 'csv':
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['name', 'phone', 'level', 'status'])
                    writer.writeheader()
                    writer.writerows(accounts)
            elif format == 'txt':
                with open(filepath, 'w', encoding='utf-8') as f:
                    for acc in accounts:
                        f.write(f"{acc['name']}|{acc['phone']}|{acc.get('level', 1)}|{acc.get('status', 'active')}\n")
            elif format == 'json':
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(accounts, f, indent=2, ensure_ascii=False)
            
            log_success(f"Exported {len(accounts)} accounts to {filepath}")
            return True
            
        except Exception as e:
            log_error(f"Export failed: {e}")
            return False
    
    def get_import_history(self, limit: int = 20) -> List[Dict]:
        """Get recent import history"""
        return self._import_history[-limit:]
    
    def get_import_stats(self) -> Dict:
        """Get import statistics"""
        total_imports = len(self._import_history)
        total_imported = sum(h.get('imported', 0) for h in self._import_history)
        total_failed = sum(h.get('failed', 0) for h in self._import_history)
        
        by_type = {}
        for h in self._import_history:
            t = h.get('import_type', 'unknown')
            by_type[t] = by_type.get(t, 0) + 1
        
        return {
            "total_imports": total_imports,
            "total_imported": total_imported,
            "total_failed": total_failed,
            "by_type": by_type,
            "success_rate": (total_imported / (total_imported + total_failed) * 100) if (total_imported + total_failed) > 0 else 0
        }

# Global instance
import_manager = ImportManager()

__all__ = ["ImportManager", "ImportResult", "ImportValidator", "import_manager"]