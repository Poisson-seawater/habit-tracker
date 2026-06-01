import re

class ParserError(Exception):
    pass

def parse_command(text: str) -> dict:
    """
    Parses a Telegram bot command text and extracts structured arguments.
    Raises ParserError on validation failure.
    """
    if not text:
        raise ParserError("Message vide.")
        
    text = text.strip()
    if not text.startswith("/"):
        raise ParserError("Les commandes doivent commencer par /.")
        
    parts = text.split(maxsplit=1)
    cmd = parts[0]
    args_str = parts[1].strip() if len(parts) > 1 else ""
    
    if cmd == "/done":
        if not args_str:
            raise ParserError("Usage : /done [nom_habitude]\nExemple : /done routine_matin")
        return {"command": "done", "habit_name": args_str}
        
    elif cmd == "/log":
        if not args_str:
            raise ParserError("Usage : /log [nom_habitude] [valeur][unité]\nExemple : /log lecture 30min")
            
        log_parts = args_str.split(maxsplit=1)
        if len(log_parts) < 2:
            raise ParserError("Usage : /log [nom_habitude] [valeur][unité]\nExemple : /log lecture 30min")
            
        habit_name = log_parts[0]
        val_unit_str = log_parts[1].strip()
        
        match = re.match(r"^(\d+)\s*([a-zA-Z]+)$", val_unit_str)
        if not match:
            raise ParserError("Usage : /log [nom_habitude] [valeur][unité]\nExemple : /log lecture 30min")
            
        val = int(match.group(1))
        unit = match.group(2)
        return {"command": "log", "habit_name": habit_name, "value": val, "unit": unit}
        
    elif cmd == "/skip":
        if not args_str:
            raise ParserError("Usage : /skip [nom_habitude] raison: [votre raison]\nExemple : /skip nage raison: fatigue extreme")
            
        skip_parts = args_str.split(maxsplit=1)
        if len(skip_parts) < 2:
            raise ParserError("Usage : /skip [nom_habitude] raison: [votre raison]\nExemple : /skip nage raison: fatigue extreme")
            
        habit_name = skip_parts[0]
        rest = skip_parts[1].strip()
        
        if not rest.startswith("raison:"):
            raise ParserError("Usage : /skip [nom_habitude] raison: [votre raison]\nExemple : /skip nage raison: fatigue extreme")
            
        reason = rest.replace("raison:", "", 1).strip()
        if not reason:
            raise ParserError("Usage : /skip [nom_habitude] raison: [votre raison]\nExemple : /skip nage raison: fatigue extreme")
            
        return {"command": "skip", "habit_name": habit_name, "reason": reason}
        
    elif cmd == "/status":
        if args_str != "today":
            raise ParserError("Usage : /status today")
        return {"command": "status", "target": "today"}
        
    elif cmd == "/set-day":
        if not args_str:
            raise ParserError("Usage : /set-day [nom_template]\nExemple : /set-day sick")
        return {"command": "set-day", "template_name": args_str}
        
    else:
        raise ParserError(f"Commande inconnue : {cmd}")
