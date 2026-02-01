"""
Action Sequence Executor - Improved command interpreter with loops, variables, and conditionals.
"""

import time
import pyautogui


class ActionSequenceExecutor:
    """Executes action sequences with loops, variables, and conditionals."""
    
    def __init__(self, config_manager, global_settings, initial_spam_count=0):
        self.config = config_manager
        self.global_settings = global_settings
        self.spam_count = initial_spam_count
        self.variables = {}
        self.lines = []
        self.pc = 0  # Program counter
    
    def execute(self, action_sequence: str):
        """Parse and execute an action sequence.
        
        Supported commands:
        - click: Click at configured position
        - Any key name: Press that key (e.g., 'e', 'space', 'escape', 'enter')
        - wait:N: Wait N milliseconds
        - set varname value: Set a variable
        - loop N: Start a loop that repeats N times
        - loop $varname: Loop using variable value
        - endloop: End loop block
        - if condition: Conditional block (e.g., if $count > 0)
        - endif: End conditional block
        
        Variables are accessed with $ prefix (e.g., $count)
        Conditions: $var > value, $var < value, $var == value, $var != value
        """
        self.lines = [line.strip() for line in action_sequence.strip().split('\n')]
        self.pc = 0
        
        while self.pc < len(self.lines):
            self._execute_line()
            self.pc += 1
    
    def _execute_line(self):
        """Execute a single line."""
        line = self.lines[self.pc]
        
        if not line or line.lower().startswith('#'):
            return  # Skip empty lines and comments
        
        line_lower = line.lower()
        
        # Handle click
        if line_lower == 'click':
            click_pos = self.global_settings.get("click_position", default={"x": 960, "y": 540})
            pyautogui.click(click_pos["x"], click_pos["y"])
        
        # Handle wait
        elif line_lower.startswith('wait:'):
            try:
                ms = int(line_lower.split(':')[1])
                time.sleep(ms / 1000.0)
            except (ValueError, IndexError):
                pass
        
        # Handle variable setting
        elif line_lower.startswith('set '):
            parts = line.split(None, 2)
            if len(parts) >= 3:
                varname = parts[1]
                value = self._evaluate(parts[2])
                self.variables[varname] = value
        
        # Handle loop
        elif line_lower.startswith('loop '):
            self._handle_loop(line)
        
        # Handle if statement
        elif line_lower.startswith('if '):
            self._handle_if(line)
        
        # Handle key press
        elif line_lower not in ['endloop', 'endif']:
            # Replace variables in the line
            key = self._replace_variables(line)
            if key:
                pyautogui.press(key.lower())
                self.spam_count += 1
    
    def _handle_loop(self, line: str):
        """Handle loop block execution."""
        try:
            parts = line.split(None, 1)
            loop_spec = parts[1] if len(parts) > 1 else ""
            
            # Determine loop count
            if loop_spec.isdigit():
                count = int(loop_spec)
            else:
                # Variable reference
                count = self.variables.get(loop_spec, 0)
                if isinstance(count, str):
                    count = int(count) if count.isdigit() else 0
            
            # Find matching endloop
            start_pc = self.pc + 1
            end_pc = self._find_matching_block_end('endloop', start_pc)
            
            if end_pc == -1:
                return
            
            # Execute loop
            for _ in range(count):
                saved_pc = self.pc
                self.pc = start_pc
                
                while self.pc < end_pc:
                    self._execute_line()
                    self.pc += 1
                
                self.pc = saved_pc
            
            # Jump past endloop
            self.pc = end_pc
        except (ValueError, IndexError):
            pass
    
    def _handle_if(self, line: str):
        """Handle if statement block."""
        try:
            condition_str = line[3:].strip()  # Remove 'if '
            
            # Evaluate condition
            if self._evaluate_condition(condition_str):
                # Find matching endif
                start_pc = self.pc + 1
                end_pc = self._find_matching_block_end('endif', start_pc)
                
                if end_pc == -1:
                    return
                
                # Execute if block
                saved_pc = self.pc
                self.pc = start_pc
                
                while self.pc < end_pc:
                    self._execute_line()
                    self.pc += 1
                
                self.pc = saved_pc
                # Jump past endif
                self.pc = end_pc
            else:
                # Skip to endif
                end_pc = self._find_matching_block_end('endif', self.pc + 1)
                if end_pc != -1:
                    self.pc = end_pc
        except Exception:
            pass
    
    def _find_matching_block_end(self, block_end_keyword: str, start_from: int) -> int:
        """Find the line number of the matching end keyword."""
        depth = 1
        for i in range(start_from, len(self.lines)):
            line = self.lines[i].lower().strip()
            
            if line.startswith('loop '):
                depth += 1
            elif line == 'endloop' and block_end_keyword == 'endloop':
                depth -= 1
                if depth == 0:
                    return i
            
            if line.startswith('if '):
                depth += 1
            elif line == 'endif' and block_end_keyword == 'endif':
                depth -= 1
                if depth == 0:
                    return i
        
        return -1
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition string like '$count > 5' or '$flag == true'."""
        operators = ['>=', '<=', '!=', '==', '>', '<']
        
        for op in operators:
            if op in condition:
                parts = condition.split(op)
                if len(parts) == 2:
                    left = self._evaluate(parts[0].strip())
                    right = self._evaluate(parts[1].strip())
                    
                    if op == '>':
                        return left > right
                    elif op == '<':
                        return left < right
                    elif op == '>=':
                        return left >= right
                    elif op == '<=':
                        return left <= right
                    elif op == '==':
                        return left == right
                    elif op == '!=':
                        return left != right
        
        return False
    
    def _evaluate(self, value_str: str):
        """Evaluate a value string (variable or literal)."""
        value_str = value_str.strip().lower()
        
        # Variable reference
        if value_str.startswith('$'):
            varname = value_str[1:]
            val = self.variables.get(varname, 0)
            return int(val) if isinstance(val, str) and val.isdigit() else val
        
        # Boolean
        if value_str == 'true':
            return 1
        if value_str == 'false':
            return 0
        
        # Number
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            return value_str
    
    def _replace_variables(self, text: str) -> str:
        """Replace variable references in text."""
        result = text
        for varname, value in self.variables.items():
            result = result.replace(f'${varname}', str(value))
        return result
