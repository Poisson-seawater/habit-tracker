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
    if "@" in cmd:
        cmd = cmd.split("@", 1)[0]
    args_str = parts[1].strip() if len(parts) > 1 else ""
    
    if cmd == "/done":
        if not args_str:
            raise ParserError("Usage : /done [nom_habitude]\nExemple : /done routine_matin")
        return {"command": "done", "habit_name": args_str}
        
    elif cmd == "/log":
        if not args_str:
            return {"command": "log", "habit_name": None, "value": None, "unit": None}
            
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
        
    elif cmd == "/fail":
        if not args_str:
            raise ParserError("Usage : /fail [nom_notodo]\nExemple : /fail Snooze")
        return {"command": "fail", "notodo_name": args_str}
        
    elif cmd == "/status":
        return {"command": "status", "target": "today"}
        
    elif cmd in ["/set-day", "/template"]:
        # No argument → listener shows template choice buttons.
        if not args_str:
            return {"command": "set-day", "template_name": None}
        return {"command": "set-day", "template_name": args_str}
        
    elif cmd in ["/aide", "/help"]:
        return {"command": "aide"}
        
    elif cmd == "/motivation":
        return {"command": "motivation"}

    elif cmd == "/liste":
        # No argument → listener shows the 3 list-choice buttons.
        if not args_str:
            return {"command": "liste", "type": None}
        if args_str.lower() not in ["todo", "habit", "notodo"]:
            raise ParserError("Usage : /liste [todo|habit|notodo]\nExemple : /liste todo")
        return {"command": "liste", "type": args_str.lower()}

    elif cmd == "/add":
        # No argument → listener shows the 3 type-choice buttons.
        if not args_str:
            return {"command": "add", "type": None, "title": None}
        add_parts = args_str.split(maxsplit=1)
        if len(add_parts) < 2 and add_parts[0].lower() != "habit":
             # habit doesn't need title in /add since it just returns help, but let's be strict
             raise ParserError("Usage : /add [todo|habit|notodo] [titre]\nExemple : /add todo Faire les courses")
             
        add_type = add_parts[0].lower()
        if add_type not in ["todo", "habit", "notodo"]:
            raise ParserError("Type inconnu. Usage : /add [todo|habit|notodo] [titre]")
            
        title = add_parts[1].strip() if len(add_parts) > 1 else ""
        return {"command": "add", "type": add_type, "title": title}
        
    elif cmd == "/add_habit":
        if not args_str:
            raise ParserError("Usage : /add_habit [binary|quant] [titre] [unité optionnelle]")
        habit_parts = args_str.split(maxsplit=2)
        if len(habit_parts) < 2:
            raise ParserError("Usage : /add_habit [binary|quant] [titre]")
            
        h_type = habit_parts[0].lower()
        if h_type not in ["binary", "quant"]:
            raise ParserError("Type doit être 'binary' ou 'quant'.")
            
        h_title = habit_parts[1]
        h_unit = habit_parts[2] if len(habit_parts) > 2 else ""
        
        return {"command": "add_habit", "habit_type": h_type, "title": h_title, "unit": h_unit}
        
    elif cmd == "/shop":
        filter_type = args_str.lower() if args_str else "toutes"
        if filter_type not in ["toutes", "dispos", "verrouillees", "all", "unlocked", "locked"]:
            raise ParserError("Usage : /shop [toutes|dispos|verrouillees]\nExemple : /shop dispos")
        return {"command": "shop", "filter": filter_type}
        
    elif cmd == "/buy":
        if not args_str:
            return {"command": "buy", "reward_name": None}
        return {"command": "buy", "reward_name": args_str}
        
    elif cmd in ["/softskill", "/softskills", "/skills"]:
        return {"command": "softskill"}
        
    else:
        raise ParserError(f"Commande inconnue : {cmd}")
