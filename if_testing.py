import re
from dataclasses import dataclass

instruction_types = {
    "Keywords": {
        "Include Keyword": r'must contain the word ["\']?(\w+)["\']?(?:\.|$)',
        "Exclude Keyword": r'NOT contain the word ["\']?(\w+)["\']?(?:\.|$)',
        "Keyword Frequency": r'contain the word ["\']?(\w+)["\']? (\d+) times(?:\.|$)',
        "Keyword Frequency Floor": r'use the word ["\']?(\w+)["\']? at least (\d+) times(?:\.|$)',
        "Keyword Order": r'your response must use the word ["\']?(\w+)["\']? before the word ["\']?(\w+)["\']?(?: and must contain both)?(?:\.|$)',
        "Keyword Pairings": r'use the words ["\']?(\w+)["\']? and ["\']?(\w+)["\']? consecutively(?:\.|$)',
        "First Occurrence Keyword": r'begin with the word ["\']?(\w+)["\']?(?:\.|$)',
        "Last Occurrence Keyword": r'end with the word ["\']?(\w+)["\']?(?:\.|$)'
    },
    "Detectable Format" : {
        "Title":r"Your response must start with a title, wrapped in double angular brackets such as <<title>>\.?",
        "Letter/Email Format": r"written in the format of a letter",
        "Schedule Format": r"written in the format of a schedule",
        "List Format": r"written in the form of a list",
    }, 
    "Length Constraints" : {
        "Maximum Words": r"not exceed (\d+) words(?:\.|$)",
        "Minimum Words": r"be longer than (\d+) words(?:\.|$)"
    },
    "Change Cases" : {
        "All Uppercase": r"written in all uppercase(?:\.|$)",
        "All Lowercase": r"written in all lowercase(?:\.|$)",
    },
    "Start/End With" : {
        "Start Checker": r'start with the phrase ["\']?(.+?)["\']?(?:\.|$)',
        "End Checker": r'end with the phrase ["\']?(.+?)["\']?(?:\.|$)',
    }
}
@dataclass
class Input:
  key: int
  prompt: str
  response: str
  instruction_id: list[str]

class CustomError(Exception):
    def __init__(self, message):
        super().__init__(message)

class KeywordChecker:
    def keyword_eval(self, instruction):
        ins_type = None
        for group, itype in instruction.instruction_id:
            if group == "Keywords":
                ins_type = itype
                break
        prompt, response = instruction.prompt, instruction.response
        pattern = instruction_types["Keywords"][ins_type]
        match = re.search(pattern, prompt, re.IGNORECASE)
        if ins_type == "Include Keyword":
            keyword = match.group(1)
            return keyword in response
        elif ins_type == "Exclude Keyword":
            keyword = match.group(1).strip().lower()
            return keyword not in response.lower()
        elif ins_type == "Keyword Frequency":
            keyword, freq = match.group(1), int(match.group(2))
            count = len(re.findall(rf'\b{re.escape(keyword)}\b', response, flags=re.IGNORECASE))
            return count == freq
        elif ins_type == "Keyword Frequency Floor":
            keyword, freq = match.group(1), int(match.group(2))
            count = len(re.findall(rf'\b{re.escape(keyword)}\b', response, flags=re.IGNORECASE))
            return count >= freq
        elif ins_type == "Keyword Order":
            keyword_1, keyword_2 = match.group(1), match.group(2)
            words = response.split()
            return words.index(keyword_1) < words.index(keyword_2)
        elif ins_type == "Keyword Pairings":
            keyword_1, keyword_2 = match.group(1), match.group(2)
            words = response.split()
            return abs(words.index(keyword_1) - words.index(keyword_2)) == 1
        elif ins_type == "First Occurrence Keyword":
            keyword = match.group(1)
            return response.split()[0].lower() == keyword.lower()
        elif ins_type == "Last Occurrence Keyword":
            keyword = match.group(1)
            if response[-1] == ".":
                last_word = response.split()[-1][:-1].lower()
            else:
                last_word = response.split()[-1].lower()
            return last_word == keyword.lower()       
        
        raise CustomError("Unknown Instruction Type")
    
    
class LengthChecker:
    def length_eval(self, instruction):
        ins_type = None
        for group, itype in instruction.instruction_id:
            if group == "Length Constraints":
                ins_type = itype
                break
        prompt, response = instruction.prompt, instruction.response
        pattern = instruction_types["Length Constraints"][ins_type]
        match = re.search(pattern, prompt)
        if ins_type == "Maximum Words":
            limit = int(match.group(1))
            return len(response.split()) <= limit
        elif ins_type == "Minimum Words":
            floor = int(match.group(1))
            return len(response.split()) >= floor
        
        raise CustomError("Unknown Instruction Type")
    
class CaseChecker:
    def case_eval(self, instruction):
        ins_type = None
        for group, itype in instruction.instruction_id:
            if group == "Change Cases":
                ins_type = itype
                break
        _, response = instruction.prompt, instruction.response
        if ins_type not in {"All Uppercase", "All Lowercase"}:
            raise CustomError("Unknown Instruction Type")

        return (ins_type == "All Uppercase" and response.isupper()) or (ins_type == "All Lowercase" and not response.isupper())
        
class StartEndChecker:
    def start_end_eval(self, instruction):
        ins_type = None
        for group, itype in instruction.instruction_id:
            if group == "Start/End With":
                ins_type = itype
                break
        if ins_type is None:
            raise CustomError("No Start/End With instruction found")
            
        prompt, response = instruction.prompt, instruction.response
        pattern = instruction_types["Start/End With"][ins_type]
        match = re.search(pattern, prompt, re.IGNORECASE)
        if not match:
            raise CustomError("Instruction pattern not found in prompt")
        keyword = match.group(1).strip().strip('"\'')

        if ins_type == "Start Checker":
            return response.strip().lower().startswith(keyword.lower())
        elif ins_type == "End Checker":
            return response.strip().lower().endswith(keyword.lower())
        else:
            raise CustomError("Unknown Instruction Type for Start/End With")
        
class FormatChecker:
    def format_eval(self, instruction):
        ins_type = None
        for group, itype in instruction.instruction_id:
            if group == "Detectable Format":
                ins_type = itype
                break
        if ins_type is None:
            raise CustomError("No Start/End With instruction found")
        _, response = instruction.prompt, instruction.response
        if ins_type == "Title":
            title = title = r"<<\s*(.+?)\s*>>"
            match = re.search(title, response)
            return match is not None

        elif ins_type == "Letter/Email Format":
            greeting = greeting = r"Dear\s+([^,]+),"
            closing = r"Best Regards,"
            match1, match2 = re.search(greeting, response, re.IGNORECASE), re.search(closing, response, re.IGNORECASE)
            return (match1 is not None) and (match2 is not None)

        elif ins_type == "Schedule Format":
            pattern = r'^\(\s*\d{1,2}:\d{2}\s*[AP]M\s*,\s*[^)]+\s*\)(?:\s*//\s*\(\s*\d{1,2}:\d{2}\s*[AP]M\s*,\s*[^)]+\s*\))*\s*$'
            match = re.search(pattern, response)
            return match is not None

        elif ins_type == "List Format":
            enum, bullet = r"1. (\w+)",r'^(?:-\s+.+?(?:\s*//\s*|\s*$))+$'
            match1, match2 = re.search(enum, response) is not None, re.search(bullet, response) is not None
            return match1 or match2
        
        raise CustomError("Unknown Instruction Type")

def get_instruction_type(instruction):
    groups = instruction_types.keys()
    res = []
    for group in groups:
        for itype, pattern in instruction_types[group].items():
            if re.search(pattern, instruction.prompt, re.IGNORECASE | re.MULTILINE):
                res.append((group, itype))
                
    if len(res) == 0:
        return []

    return res


def eval_help(instruction):
    instruction.instruction_id = get_instruction_type(instruction)
    if len(instruction.instruction_id) == 0:
        return None
    res = True
    for k in instruction.instruction_id:
        group = k[0]
        if group  == "Keywords":
            checker = KeywordChecker()
            res = res & checker.keyword_eval(instruction=instruction)
        elif group == "Length Constraints":
            checker = LengthChecker()
            res = res & checker.length_eval(instruction=instruction)
        elif group == "Detectable Format": 
            checker = FormatChecker()
            res = res & checker.format_eval(instruction=instruction)
        elif group == "Change Cases":
            checker = CaseChecker()
            res = res & checker.case_eval(instruction=instruction)
        elif group == "Start/End With":
            checker = StartEndChecker()
            res = res & checker.start_end_eval(instruction=instruction)
        if not res:
            return False
    return True
    

def evaluate(instruction):
    return eval_help(instruction)

def filter_data(evaluation):
    res = []
    for key in evaluation:
        if evaluation[key] == True:
            res.append(key)
    
    return res

def make_instructions(prompt, response, key):
    return Input(key=key, prompt=prompt, response=response, instruction_id=[])


