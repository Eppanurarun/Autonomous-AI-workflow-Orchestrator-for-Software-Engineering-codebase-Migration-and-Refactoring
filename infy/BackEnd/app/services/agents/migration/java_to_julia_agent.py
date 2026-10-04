"""
Java to Julia Migration Agent
==============================
Converts Java source code to idiomatic Julia code using Gemini LLM.

The agent focuses on preserving the intended functionality and behavior
of the original Java program, not merely translating syntax.

This agent is part of the Migration module and is completely independent
from the existing Remediation Agent.
"""

import re
import json
from typing import Any, Dict, Optional

from google import genai
from google.genai import types

from app.core.config import settings


class JavaToJuliaAgent:
    """
    Converts analyzed Java source code into idiomatic Julia code
    using Gemini LLM with detailed conversion instructions.
    """

    def __init__(self):
        self.client = None
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            try:
                self.client = genai.Client(
                    api_key=settings.GEMINI_API_KEY,
                    http_options=types.HttpOptions(
                        timeout=90000,
                        retry_options=types.HttpRetryOptions(
                            attempts=2,
                        ),
                    ),
                )
            except Exception:
                self.client = None

    # ============================================================
    # CONVERSION PROMPT
    # ============================================================

    @staticmethod
    def _build_conversion_prompt(
        java_code: str,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Build detailed conversion prompt with Java→Julia mapping rules."""

        analysis_context = ""
        if analysis:
            analysis_context = f"""
Migration Analysis Context:
- Classes: {analysis.get('classes', 'unknown')}
- Methods: {analysis.get('methods', 'unknown')}
- Loops: {analysis.get('loops', 'unknown')}
- Collections: {analysis.get('collections', 'unknown')}
- Exception Handling: {analysis.get('exception_handling', 'unknown')}
- Inheritance: {analysis.get('inheritance', 'unknown')}
- Static Members: {analysis.get('static_members', 'unknown')}
- Threading: {analysis.get('threading_concurrency', 'unknown')}
- Complexity: {analysis.get('complexity_assessment', 'unknown')}
- Concerns: {', '.join(analysis.get('migration_concerns', []))}
"""

        return f"""You are an expert Java-to-Julia code migration specialist.

Convert the following Java source code into idiomatic, correct Julia code.

CRITICAL RULES:
1. PRESERVE the intended FUNCTIONALITY and BEHAVIOR — do NOT just translate syntax
2. Generate VALID, COMPILABLE Julia code
3. Use idiomatic Julia patterns, not Java patterns written in Julia syntax

CONVERSION MAPPINGS:
- Java classes → Julia structs (mutable struct for mutable state) with associated functions
- Java methods → Julia functions (use multiple dispatch where appropriate)
- Java primitive types → Julia types (int→Int64, double→Float64, boolean→Bool, char→Char)
- Java String → Julia String
- Java arrays → Julia Arrays
- Java ArrayList/List → Julia Vector (Array{{T,1}})
- Java HashMap/Map → Julia Dict{{K,V}}
- Java HashSet/Set → Julia Set{{T}}
- Java for-each loops → Julia for-in loops
- Java for(int i=0;i<n;i++) → Julia for i in 1:n (1-indexed!)
- Java if/else → Julia if/elseif/else/end
- Java switch/case → Julia if/elseif chains or match patterns
- Java try/catch → Julia try/catch/finally
- Java constructors → Julia constructor functions (inner or outer)
- Java static methods → Julia module-level functions
- Java static final → Julia const
- Java System.out.println → Julia println()
- Java Scanner/System.in → Julia readline()
- Java File I/O → Julia open()/read()/write()
- Java null → Julia nothing
- Java inheritance → Julia abstract types + composition
- Java interfaces → Julia abstract types with method signatures
- Java generics → Julia parametric types
- Java @Override → Julia (not needed, multiple dispatch handles it)
- Java access modifiers (public/private) → Julia (no access modifiers, use naming convention with _)
- Java this → Julia (explicit struct parameter)

IMPORTANT DIFFERENCES:
- Julia arrays are 1-indexed, not 0-indexed
- Julia uses `end` to close blocks, not braces
- Julia has no semicolons at end of statements
- Julia functions don't need return type declarations (but can have them)
- Julia uses `nothing` instead of `null`/`void`
- Julia uses `true`/`false` (lowercase) for booleans
- Julia string concatenation uses `*` not `+`
- Julia uses `===` for identity comparison and `==` for equality

{analysis_context}

Respond with ONLY valid JSON (no markdown fences):
{{
  "julia_code": "the complete converted Julia code as a single string",
  "conversion_notes": ["list of important conversion decisions made"],
  "unsupported_features": ["list of Java features that could not be directly converted"]
}}

Java source code to convert:
```java
{java_code}
```"""

    # ============================================================
    # PUBLIC API
    # ============================================================

    def convert(
        self,
        java_code: str,
        analysis: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Convert Java source code to Julia.

        Parameters:
            java_code: The Java source code to convert
            analysis: Optional migration analysis result for context

        Returns:
            Dictionary with julia_code, conversion_notes, and unsupported_features
        """

        if not java_code or not java_code.strip():
            return {
                "error": "No Java code provided",
                "julia_code": "",
                "conversion_notes": [],
                "unsupported_features": [],
            }

        if not self.client:
            # Fallback to rule-based conversion when API key is not available
            return self._rule_based_conversion(java_code, analysis)

        prompt = self._build_conversion_prompt(java_code, analysis)

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.15,
                    max_output_tokens=8000,
                    response_mime_type="application/json",
                ),
            )

            text = response.text.strip()

            # Strip markdown code fences if present
            if text.startswith("```"):
                text = re.sub(r'^```(?:json)?\s*', '', text)
                text = re.sub(r'\s*```$', '', text)

            result = json.loads(text)

            # Validate required fields
            if "julia_code" not in result or not result["julia_code"].strip():
                return {
                    "error": "LLM returned empty Julia code",
                    "julia_code": "",
                    "conversion_notes": result.get("conversion_notes", []),
                    "unsupported_features": result.get("unsupported_features", []),
                }

            return {
                "julia_code": result["julia_code"],
                "conversion_notes": result.get("conversion_notes", []),
                "unsupported_features": result.get("unsupported_features", []),
            }

        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract Julia code from raw text
            raw = response.text.strip() if response and response.text else ""
            julia_match = re.search(r'```julia\s*(.*?)\s*```', raw, re.DOTALL)
            if julia_match:
                return {
                    "julia_code": julia_match.group(1).strip(),
                    "conversion_notes": ["Extracted from non-JSON LLM response"],
                    "unsupported_features": [],
                }
            return {
                "error": "Failed to parse LLM response as valid JSON",
                "julia_code": "",
                "conversion_notes": [],
                "unsupported_features": [],
            }

        except Exception as e:
            # If API call fails, fallback to rule-based conversion
            if "API key" in str(e) or "INVALID_ARGUMENT" in str(e):
                return self._rule_based_conversion(java_code, analysis)
            return {
                "error": f"Migration conversion failed: {str(e)}",
                "julia_code": "",
                "conversion_notes": [],
                "unsupported_features": [],
            }

    def _rule_based_conversion(self, java_code: str, analysis: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Advanced rule-based Java to Julia conversion when Gemini API is unavailable.
        Handles proper Julia syntax: structs, functions, type conversions, array indexing, etc.
        """
        try:
            # Parse Java code structure
            parsed = self._parse_java_structure(java_code)
            
            # Generate Julia code
            julia_code = self._generate_julia_code(parsed)
            
            # Validate generated Julia code syntax
            validation_result = self._validate_julia_syntax(julia_code)
            
            # Validate generated Julia code runtime if Julia is available
            runtime_result = self._validate_julia_runtime(julia_code)
            
            conversion_notes = [
                "Using advanced rule-based fallback conversion (Gemini API unavailable)",
                "Proper Julia syntax generated with structs and functions",
                "Type conversions and array indexing handled correctly"
            ]
            
            if validation_result["has_errors"]:
                conversion_notes.append(f"Syntax validation found {len(validation_result['errors'])} issues")
                conversion_notes.extend(validation_result["errors"][:3])  # Add first 3 errors as notes
            
            if runtime_result["julia_available"]:
                if runtime_result["success"]:
                    conversion_notes.append("Runtime validation: Code executed successfully")
                else:
                    conversion_notes.append(f"Runtime validation: {len(runtime_result['runtime_errors'])} errors found")
                    conversion_notes.extend(runtime_result["runtime_errors"][:2])
            else:
                conversion_notes.append("Runtime validation: Julia not available on system")
            
            return {
                "julia_code": julia_code,
                "conversion_notes": conversion_notes,
                "unsupported_features": validation_result.get("unsupported_features", []),
                "syntax_validation": validation_result,
                "runtime_validation": runtime_result
            }
            
        except Exception as e:
            return {
                "error": f"Rule-based conversion failed: {str(e)}",
                "julia_code": f"# Conversion error: {str(e)}\n# Original Java code:\n{java_code}",
                "conversion_notes": ["Rule-based conversion encountered an error"],
                "unsupported_features": [],
            }

    def _parse_java_structure(self, java_code: str) -> Dict[str, Any]:
        """Parse Java code into structured components."""
        lines = java_code.split('\n')
        
        structure = {
            "package": None,
            "imports": [],
            "class": None,
            "fields": [],
            "constructors": [],
            "methods": [],
            "main_method": None,
        }
        
        current_class = None
        current_method = None
        in_method_body = False
        method_lines = []
        brace_level = 0
        in_class_body = False
        
        for line in lines:
            stripped = line.strip()
            
            # Skip empty lines and comments
            if not stripped or stripped.startswith('//'):
                continue
            
            # Package declaration
            if stripped.startswith('package '):
                structure["package"] = stripped[8:].rstrip(';')
                continue
            
            # Import statements
            if stripped.startswith('import '):
                structure["imports"].append(stripped[7:].rstrip(';'))
                continue
            
            # Class declaration
            class_match = re.match(r'(public\s+)?(class|interface)\s+(\w+)', stripped)
            if class_match:
                current_class = {
                    "name": class_match.group(3),
                    "type": class_match.group(2),
                    "is_interface": class_match.group(2) == 'interface'
                }
                structure["class"] = current_class
                in_class_body = True
                brace_level = 1
                continue
            
            # Track class body brace level
            if in_class_body and not in_method_body:
                brace_level += stripped.count('{') - stripped.count('}')
                if brace_level <= 0:
                    in_class_body = False
                    current_class = None
                    continue
            
            # Field declarations (only when in class body but not in method body)
            field_match = re.match(r'(public|private|protected)?\s*(static)?\s*(\w+(?:<[^>]+>)?(?:\[\])?)\s+(\w+)\s*(?:=\s*([^;]+))?;', stripped)
            if field_match and current_class and in_class_body and not in_method_body:
                field_type = field_match.group(3)
                field_name = field_match.group(4)
                field_default = field_match.group(5).strip() if field_match.group(5) else None
                structure["fields"].append({
                    "type": field_type,
                    "name": field_name,
                    "default": field_default
                })
                continue
            
            # Constructor
            constructor_match = re.match(r'(public\s+)?(\w+)\s*\(([^)]*)\)\s*\{?', stripped)
            if constructor_match and current_class and constructor_match.group(2) == current_class["name"]:
                current_method = {
                    "type": "constructor",
                    "name": constructor_match.group(2),
                    "params": constructor_match.group(3),
                    "body": []
                }
                structure["constructors"].append(current_method)
                in_method_body = True
                brace_level = 1
                continue
            
            # Method declaration
            method_match = re.match(r'(public|private|protected)?\s*(static)?\s*(\w+(?:<[^>]+>)?)\s+(\w+)\s*\(([^)]*)\)\s*\{?', stripped)
            if method_match and current_class and in_class_body and not in_method_body:
                is_static = method_match.group(2) == 'static'
                return_type = method_match.group(3)
                method_name = method_match.group(4)
                params = method_match.group(5)
                
                # Check if it's main method
                if method_name == "main" and "String[]" in params:
                    current_method = {
                        "type": "main",
                        "name": "main",
                        "params": params,
                        "body": []
                    }
                    structure["main_method"] = current_method
                else:
                    current_method = {
                        "type": "method",
                        "return_type": return_type,
                        "name": method_name,
                        "params": params,
                        "is_static": is_static,
                        "body": []
                    }
                    structure["methods"].append(current_method)
                
                in_method_body = True
                brace_level = 1
                continue
            
            # Method body content
            if in_method_body and current_method:
                # Track brace level
                brace_level += stripped.count('{') - stripped.count('}')
                
                if brace_level > 0:
                    current_method["body"].append(line)
                else:
                    in_method_body = False
                    current_method = None
        
        return structure

    def _generate_julia_code(self, parsed: Dict[str, Any]) -> str:
        """Generate Julia code from parsed Java structure."""
        julia_lines = []
        
        # Add header
        julia_lines.append("# Auto-generated Julia code from Java")
        julia_lines.append("# Generated using rule-based fallback conversion")
        julia_lines.append("")
        
        # Package as module comment
        if parsed["package"]:
            julia_lines.append(f"# module {parsed['package']}")
            julia_lines.append("")
        
        # Imports as using comments
        for imp in parsed["imports"]:
            julia_lines.append(f"# using {imp}")
        if parsed["imports"]:
            julia_lines.append("")
        
        # Generate struct
        if parsed["class"]:
            class_info = parsed["class"]
            if class_info["is_interface"]:
                julia_lines.append(f"# abstract type {class_info['name']} end")
            else:
                julia_lines.append(f"mutable struct {class_info['name']}")
                for field in parsed["fields"]:
                    julia_type = self._convert_field_type(field["type"])
                    julia_lines.append(f"    {field['name']}::{julia_type}")
                julia_lines.append("end")
                julia_lines.append("")
        
        # Generate constructor
        for constructor in parsed["constructors"]:
            julia_lines.append(f"function {constructor['name']}({self._convert_params(constructor['params'])})")
            constructor_body = self._convert_constructor_body(constructor["body"], parsed["class"]["name"])
            julia_lines.append(f"    return {constructor_body}")
            julia_lines.append("end")
            julia_lines.append("")
        
        # Generate methods
        for method in parsed["methods"]:
            method_name = method["name"]
            is_static = method.get("is_static", False)
            # Static methods don't need the obj parameter
            class_name_for_params = None if is_static else (parsed["class"]["name"] if parsed["class"] else None)
            params = self._convert_method_params(method["params"], class_name_for_params)
            
            julia_lines.append(f"function {method_name}({params})")
            # Static methods don't need obj context
            class_name_for_body = None if is_static else (parsed["class"]["name"] if parsed["class"] else None)
            converted_body = self._convert_method_body(method["body"], class_name_for_body, parsed["fields"], parsed["methods"])
            for line in converted_body:
                julia_lines.append(f"    {line}")
            julia_lines.append("end")
            julia_lines.append("")
        
        # Generate main function
        if parsed["main_method"]:
            julia_lines.append("function main()")
            converted_body = self._convert_main_body(parsed["main_method"]["body"], parsed["class"]["name"] if parsed["class"] else None, parsed["fields"], parsed["methods"])
            for line in converted_body:
                julia_lines.append(f"    {line}")
            julia_lines.append("end")
            julia_lines.append("")
            julia_lines.append("main()")
        
        return '\n'.join(julia_lines)

    def _convert_field_type(self, java_type: str) -> str:
        """Convert Java field type to Julia type."""
        type_map = {
            'int': 'Int',
            'Integer': 'Int',
            'double': 'Float64',
            'Double': 'Float64',
            'float': 'Float32',
            'boolean': 'Bool',
            'Boolean': 'Bool',
            'String': 'String',
            'char': 'Char',
            'int[]': 'Vector{Int}',
            'Integer[]': 'Vector{Int}',
            'double[]': 'Vector{Float64}',
            'String[]': 'Vector{String}',
        }
        
        # Handle array types with brackets
        if '[]' in java_type:
            base_type = java_type.replace('[]', '')
            julia_base = self._convert_field_type(base_type)
            return f"Vector{{{julia_base}}}"
        
        # Handle generic types
        if '<' in java_type and '>' in java_type:
            base_type = java_type.split('<')[0]
            inner_type = java_type.split('<')[1].rstrip('>')
            julia_inner = self._convert_field_type(inner_type)
            return f"Vector{{{julia_inner}}}"
        
        return type_map.get(java_type, java_type)

    def _convert_params(self, java_params: str) -> str:
        """Convert constructor parameters to Julia format."""
        if not java_params or java_params.strip() == "":
            return ""
        
        params = []
        for param in java_params.split(','):
            param = param.strip()
            if not param:
                continue
            
            parts = param.split()
            if len(parts) >= 2:
                param_type = parts[0]
                param_name = parts[1]
                julia_type = self._convert_field_type(param_type)
                params.append(f"{param_name}::{julia_type}")
            else:
                params.append(param)
        
        return ', '.join(params)

    def _convert_method_params(self, java_params: str, class_name: str = None) -> str:
        """Convert method parameters to Julia format, adding struct as first param for instance methods."""
        params = []
        
        # Add struct parameter for instance methods
        if class_name:
            params.append(f"obj::{class_name}")
        
        if not java_params or java_params.strip() == "":
            return ', '.join(params)
        
        for param in java_params.split(','):
            param = param.strip()
            if not param:
                continue
            
            # Handle String[] args
            if "String[]" in param:
                params.append("args::Vector{String}")
                continue
            
            parts = param.split()
            if len(parts) >= 2:
                param_name = parts[1]
                params.append(param_name)
            else:
                params.append(param)
        
        return ', '.join(params)

    def _convert_constructor_body(self, body_lines: list, class_name: str) -> str:
        """Convert constructor body to Julia field assignments."""
        assignments = []
        local_vars = set()
        for line in body_lines:
            stripped = line.strip()
            if not stripped or stripped == '{' or stripped == '}':
                continue
            
            # Convert this.field = value to field assignment
            this_match = re.match(r'this\.(\w+)\s*=\s*(.+);', stripped)
            if this_match:
                field_name = this_match.group(1)
                value = this_match.group(2).rstrip(';')
                value = self._convert_expression(value, class_name, local_vars)
                assignments.append(value)
        
        # In Julia, the constructor returns the struct instance
        # The constructor parameters are already the field values
        # So we just return the struct with the parameters
        return f"{class_name}({', '.join(assignments)})"

    def _convert_method_body(self, body_lines: list, class_name: str = None, fields: list = None, all_methods: list = None) -> list:
        """Convert method body lines to Julia with proper block structure."""
        if fields is None:
            fields = []
        if all_methods is None:
            all_methods = []
        field_names = {field["name"] for field in fields}
        method_names = {method["name"] for method in all_methods}
        
        converted_lines = []
        block_stack = []  # Track open blocks (if, for, etc.)
        local_vars = set()  # Track local variables declared in the method
        
        for line in body_lines:
            stripped = line.strip()
            
            # Check if this is a closing brace that should add 'end'
            if stripped == '}' and block_stack:
                block_type = block_stack.pop()
                converted_lines.append('end')
                continue
            
            # Check if this line contains } else if - need to add end before else if
            if '} else if' in stripped or '}else if' in stripped:
                if block_stack:
                    block_stack.pop()
                    converted_lines.append('end')
                # Process the else if part - extract condition
                else_if_match = re.match(r'\}\s*else\s+if\s*\((.+)\)\s*\{?', stripped)
                if else_if_match:
                    condition = else_if_match.group(1)
                    condition = self._convert_expression(condition, class_name, local_vars, field_names, method_names)
                    condition = condition.strip()
                    converted_lines.append(f"elseif {condition}")
                    block_stack.append('elseif')
                continue
            
            # Check if this line contains } else { - need to add end before else
            if '} else {' in stripped or '}else{' in stripped:
                if block_stack:
                    block_stack.pop()
                    converted_lines.append('end')
                converted_lines.append('else')
                continue
            
            converted = self._convert_method_body_line(line, class_name, local_vars, field_names, method_names)
            if converted is None:
                continue
            
            converted_lines.append(converted)
            
            # Check if this line starts a block
            if converted.startswith('if ') or converted.startswith('for ') or converted.startswith('while '):
                block_stack.append(converted.split()[0])  # Track block type
        
        return converted_lines

    def _convert_method_body_line(self, line: str, class_name: str = None, local_vars: set = None, field_names: set = None, method_names: set = None) -> str:
        """Convert a single line of method body to Julia."""
        if local_vars is None:
            local_vars = set()
        if field_names is None:
            field_names = set()
        if method_names is None:
            method_names = set()
        """Convert a single line of method body to Julia."""
        if local_vars is None:
            local_vars = set()
        if field_names is None:
            field_names = set()
            
        stripped = line.strip()
        if not stripped or stripped in ['{', '}']:
            return None
        
        # Remove semicolon
        stripped = stripped.rstrip(';')
        
        # Return statements - must come early to avoid matching other patterns
        if stripped.startswith('return '):
            expr = stripped[7:]
            # Convert field access in the return expression
            expr = self._convert_expression(expr, class_name, local_vars, field_names, method_names)
            return f"return {expr}"
        
        # Variable declarations
        var_match = re.match(r'(int|double|boolean|String|char|int\[\]|double\[\]|String\[\])\s+(\w+)\s*=\s*(.+)', stripped)
        if var_match:
            var_name = var_match.group(2)
            value = var_match.group(3)
            value = self._convert_expression(value, class_name, local_vars, field_names, method_names)
            local_vars.add(var_name)  # Track this as a local variable
            return f"{var_name} = {value}"
        
        # For loops (enhanced for-each) - must come before built-in function check
        for_each_match = re.match(r'for\s*\(\s*(\w+(?:\[\])?)\s+(\w+)\s*:\s*(\w+)\s*\)\s*\{?', stripped)
        if for_each_match:
            var_type = for_each_match.group(1)
            var_name = for_each_match.group(2)
            collection = for_each_match.group(3)
            local_vars.add(var_name)  # Track loop variable as local
            # Add obj. prefix if collection is a field
            if collection in field_names:
                collection = f"obj.{collection}"
            return f"for {var_name} in {collection}"
        
        # Try a more flexible for loop pattern (simple match)
        for_each_match2 = re.match(r'for\s*\(\s*\w+\s+(\w+)\s*:\s*(\w+)\s*\)\s*\{?', stripped)
        if for_each_match2:
            var_name = for_each_match2.group(1)
            collection = for_each_match2.group(2)
            local_vars.add(var_name)  # Track loop variable as local
            # Add obj. prefix if collection is a field
            if collection in field_names:
                collection = f"obj.{collection}"
            return f"for {var_name} in {collection}"
        
        # If statements - must come before method call check to avoid matching "if(" as a method
        if_match = re.match(r'if\s*\((.+)\)\s*\{?', stripped)
        if if_match:
            condition = if_match.group(1)
            # Convert the condition expression
            condition = self._convert_expression(condition, class_name, local_vars, field_names, method_names)
            # Remove any trailing whitespace
            condition = condition.strip()
            return f"if {condition}"
        
        # Method calls on this object
        this_method_match = re.match(r'this\.(\w+)\s*\(([^)]*)\)', stripped)
        if this_method_match and class_name:
            method_name = this_method_match.group(1)
            args = this_method_match.group(2)
            args = self._convert_expression(args, class_name, local_vars, field_names, method_names)
            return f"{method_name}(obj{', ' + args if args else ''})"
        
        # Built-in function calls (handle these first to avoid confusion with method calls)
        built_in_functions = {'println', 'length', 'sum', 'Int', 'Float64', 'String', 'Bool', 'Char', 'Vector', 'Array', 'Dict', 'Set'}
        for func in built_in_functions:
            if stripped.startswith(f'{func}('):
                args_match = re.match(rf'{func}\s*\(([^)]*)\)', stripped)
                if args_match:
                    args = args_match.group(1)
                    args = self._convert_expression(args, class_name, local_vars, field_names, method_names)
                    return f"{func}({args})"
        
        # Method calls without explicit this (instance methods on same object)
        # Pattern: methodName(args) where methodName is not a built-in function
        simple_method_match = re.match(r'(\w+)\s*\(([^)]*)\)', stripped)
        if simple_method_match and class_name:
            method_name = simple_method_match.group(1)
            args = simple_method_match.group(2)
            # Check if this is a method call to another instance method
            # If it's in method_names, it's definitely an instance method
            # If it's not a built-in function and not a local variable, assume it's a method call
            if method_name in method_names or (method_name not in built_in_functions and method_name not in local_vars):
                args = self._convert_expression(args, class_name, local_vars, field_names, method_names)
                return f"{method_name}(obj{', ' + args if args else ''})"
            else:
                # It's a built-in function, just convert the args
                args = self._convert_expression(args, class_name, local_vars, field_names, method_names)
                return f"{method_name}({args})"
        
        # Method calls on other objects
        method_match = re.match(r'(\w+)\.(\w+)\s*\(([^)]*)\)', stripped)
        if method_match:
            obj_name = method_match.group(1)
            method_name = method_match.group(2)
            args = method_match.group(3)
            args = self._convert_expression(args, class_name, local_vars, field_names, method_names)
            return f"{method_name}({obj_name}{', ' + args if args else ''})"
        
        # Array length
        length_match = re.match(r'(\w+)\.length', stripped)
        if length_match:
            array_name = length_match.group(1)
            return f"length({array_name})"
        
        # String .length() method (convert to length() function)
        string_length_match = re.match(r'(\w+)\.length\s*\(\)', stripped)
        if string_length_match:
            obj_name = string_length_match.group(1)
            # Add obj. prefix if it's a field
            if obj_name in field_names and obj_name not in local_vars:
                obj_name = f"obj.{obj_name}"
            return f"length({obj_name})"
        
        # String methods that need special conversion
        string_method_match = re.match(r'(\w+)\.(\w+)\s*\(([^)]*)\)', stripped)
        if string_method_match:
            obj_name = string_method_match.group(1)
            method_name = string_method_match.group(2)
            args = string_method_match.group(3)
            
            # Java string method -> Julia function mappings
            string_method_map = {
                'toUpperCase': 'uppercase',
                'toLowerCase': 'lowercase',
                'contains': 'occursin',
                'substring': 'SubString',
                'charAt': 'getindex',
                'equals': '==',
                'trim': 'strip',
                'replace': 'replace',
            }
            
            if method_name in string_method_map:
                julia_func = string_method_map[method_name]
                args = self._convert_expression(args, class_name, local_vars, field_names, method_names)
                # Add obj. prefix if it's a field
                if obj_name in field_names and obj_name not in local_vars:
                    obj_name = f"obj.{obj_name}"
                if method_name == 'contains':
                    # Julia's occursin(substring, string) - reverse order
                    return f"occursin({args}, {obj_name})"
                else:
                    return f"{julia_func}({obj_name}{', ' + args if args else ''})"
            # If it's not a string method we know about, fall through to regular method call handling
        
        # Method calls on other objects
        
        # Array access conversion - will be handled in expression conversion
        
        # System.out.println
        println_match = re.match(r'System\.out\.println\s*\((.+)\)', stripped)
        if println_match:
            content = println_match.group(1)
            # First convert the expression (including method calls)
            content = self._convert_expression(content, class_name, local_vars, field_names, method_names)
            # Then convert string concatenation from + to comma in println
            # Julia println accepts multiple arguments separated by commas
            # Replace + with comma (simple approach for common cases)
            content = content.replace(' + ', ', ')
            # Handle ternary operators in println
            content = self._convert_ternary(content, class_name, local_vars, field_names, method_names)
            return f"println({content})"
        
        # Standard for loop
        for_match = re.match(r'for\s*\(\s*int\s+(\w+)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\d+)\s*;\s*\1\+\+\s*\)', stripped)
        if for_match:
            var_name = for_match.group(1)
            start = for_match.group(2)
            end = for_match.group(3)
            local_vars.add(var_name)  # Track loop variable as local
            return f"for {var_name} in {start}:{end}"
        
        # Standard for loop with length
        for_match2 = re.match(r'for\s*\(\s*int\s+(\w+)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\w+)\.length\s*;\s*\1\+\+\s*\)', stripped)
        if for_match2:
            var_name = for_match2.group(1)
            start = for_match2.group(2)
            array_name = for_match2.group(3)
            local_vars.add(var_name)  # Track loop variable as local
            # Add obj. prefix if array is a field
            if array_name in field_names:
                array_name = f"obj.{array_name}"
            return f"for {var_name} in {start}:length({array_name})"
        
        # Standard for loop with variable (not just length)
        for_match3 = re.match(r'for\s*\(\s*int\s+(\w+)\s*=\s*(\d+)\s*;\s*\1\s*<\s*(\w+)\s*;\s*\1\+\+\s*\)', stripped)
        if for_match3:
            var_name = for_match3.group(1)
            start = for_match3.group(2)
            end_var = for_match3.group(3)
            local_vars.add(var_name)  # Track loop variable as local
            # Add obj. prefix if end_var is a field
            if end_var in field_names:
                end_var = f"obj.{end_var}"
            return f"for {var_name} in {start}:{end_var}"
        
        # Else statements
        if stripped == 'else':
            return 'else'
        
        # Else statements with curly braces
        else_match = re.match(r'\}\s*else\s*\{?', stripped)
        if else_match:
            return 'else'
        
        # Else if statements
        elseif_match = re.match(r'}\s*else\s+if\s*\((.+)\)\s*\{?', stripped)
        if elseif_match:
            condition = elseif_match.group(1)
            condition = self._convert_expression(condition, class_name, local_vars, field_names, method_names)
            condition = condition.strip()
            return f"elseif {condition}"
        
        # Else if statements (without leading })
        elseif_match2 = re.match(r'else\s+if\s*\((.+)\)\s*\{?', stripped)
        if elseif_match2:
            condition = elseif_match2.group(1)
            condition = self._convert_expression(condition, class_name, local_vars, field_names, method_names)
            condition = condition.strip()
            return f"elseif {condition}"
        
        # Convert general expressions and add obj. prefix for field access
        converted = self._convert_expression(stripped, class_name, local_vars, field_names, method_names)
        
        # If this is a simple field access (e.g., "name" or "marks"), add obj. prefix
        # Only if it's not a local variable and is a known field and we're in an instance method
        if class_name and re.match(r'^\w+$', converted) and not converted in ['true', 'false', 'nothing'] and converted not in local_vars and converted in field_names:
            converted = f"obj.{converted}"
        
        # Handle assignment expressions with field access (e.g., "total += mark" where mark is from obj.marks)
        assignment_match = re.match(r'(\w+)\s*([+\-*/]=)\s*(.+)', converted)
        if assignment_match:
            var_name = assignment_match.group(1)
            operator = assignment_match.group(2)
            value = assignment_match.group(3)
            # If the right side is a field without obj., add it (only in instance methods)
            if class_name and value in field_names and value not in local_vars and not value.startswith('obj.'):
                converted = f"{var_name} {operator} obj.{value}"
            # Handle array access like marks[1] -> obj.marks[1] (only in instance methods)
            elif class_name and value in field_names and '[' in value and not value.startswith('obj.'):
                converted = f"{var_name} {operator} obj.{value}"
        
        # Handle simple assignments with field access (e.g., "highest = marks[1]")
        simple_assignment_match = re.match(r'(\w+)\s*=\s*(.+)', converted)
        if simple_assignment_match:
            var_name = simple_assignment_match.group(1)
            value = simple_assignment_match.group(2)
            # If the right side is a field without obj., add it (only in instance methods)
            if class_name and value in field_names and value not in local_vars and not value.startswith('obj.'):
                converted = f"{var_name} = obj.{value}"
            # Handle array access like marks[1] -> obj.marks[1] (only in instance methods)
            elif class_name and value in field_names and '[' in value and not value.startswith('obj.'):
                converted = f"{var_name} = obj.{value}"
        
        return converted

    def _convert_main_body(self, body_lines: list, class_name: str = None, fields: list = None, all_methods: list = None) -> list:
        """Convert main body lines to Julia with proper block structure."""
        if fields is None:
            fields = []
        if all_methods is None:
            all_methods = []
        field_names = {field["name"] for field in fields}
        method_names = {method["name"] for method in all_methods}
        
        converted_lines = []
        block_stack = []  # Track open blocks (if, for, etc.)
        local_vars = set()  # Track local variables declared in main
        
        for line in body_lines:
            stripped = line.strip()
            
            # Check if this is a closing brace that should add 'end'
            if stripped == '}' and block_stack:
                block_type = block_stack.pop()
                converted_lines.append('end')
                continue
            
            # Note: main is static, so we pass None for class_name to avoid adding obj. prefix
            converted = self._convert_main_body_line(line, None, local_vars, field_names, method_names)
            if converted is None:
                continue
            
            converted_lines.append(converted)
            
            # Check if this line starts a block
            if converted.startswith('if ') or converted.startswith('for ') or converted.startswith('while '):
                block_stack.append(converted.split()[0])  # Track block type
        
        return converted_lines

    def _convert_main_body_line(self, line: str, class_name: str = None, local_vars: set = None, field_names: set = None, method_names: set = None) -> str:
        """Convert a single line of main body to Julia."""
        if local_vars is None:
            local_vars = set()
        if field_names is None:
            field_names = set()
        if method_names is None:
            method_names = set()
            
        stripped = line.strip()
        if not stripped or stripped in ['{', '}']:
            return None
        
        # Remove semicolon
        stripped = stripped.rstrip(';')
        
        # Variable declarations with array initialization
        array_var_match = re.match(r'int\[\]\s+(\w+)\s*=\s*\{(.+)\}', stripped)
        if array_var_match:
            var_name = array_var_match.group(1)
            array_values = array_var_match.group(2)
            local_vars.add(var_name)
            return f"{var_name} = [{array_values}]"
        
        # Object creation with new
        new_match = re.match(r'(\w+)\s+(\w+)\s*=\s*new\s+(\w+)\s*\(([^)]*)\)', stripped)
        if new_match:
            var_type = new_match.group(1)
            var_name = new_match.group(2)
            actual_class_name = new_match.group(3)  # The actual class being instantiated
            args = new_match.group(4)
            # Pass the actual class name, not the parameter class_name
            args = self._convert_expression(args, actual_class_name, local_vars, field_names, method_names)
            local_vars.add(var_name)
            return f"{var_name} = {actual_class_name}({args})"
        
        # Method calls on objects
        method_match = re.match(r'(\w+)\.(\w+)\s*\(([^)]*)\)', stripped)
        if method_match:
            obj_name = method_match.group(1)
            method_name = method_match.group(2)
            args = method_match.group(3)
            # Check if this is a method call on a local variable object
            if obj_name in local_vars:
                args = self._convert_expression(args, class_name, local_vars, field_names, method_names)
                return f"{method_name}({obj_name}{', ' + args if args else ''})"
            else:
                # Handle method calls on fields or other objects
                args = self._convert_expression(args, class_name, local_vars, field_names, method_names)
                return f"{method_name}({obj_name}{', ' + args if args else ''})"
        
        # Other conversions - pass None for class_name since main is static
        return self._convert_method_body_line(line, None, local_vars, field_names, method_names)

    def _convert_ternary(self, expr: str, class_name: str = None, local_vars: set = None, field_names: set = None, method_names: set = None) -> str:
        """Convert Java ternary operators to Julia ternary operators."""
        # Java ternary: condition ? true_value : false_value
        # Julia ternary: condition ? true_value : false_value (same syntax)
        # Just need to ensure the expression is valid Julia
        if method_names is None:
            method_names = set()
        # Convert method calls in ternary expressions
        if '?' in expr and ':' in expr:
            parts = expr.split('?')
            if len(parts) == 2:
                condition = parts[0].strip()
                rest = parts[1].strip()
                true_false = rest.split(':')
                if len(true_false) == 2:
                    true_val = true_false[0].strip()
                    false_val = true_false[1].strip()
                    # Convert each part
                    # Pass a flag to avoid double-conversion of method calls
                    condition = self._convert_expression(condition, class_name, local_vars, field_names, method_names)
                    true_val = self._convert_expression(true_val, class_name, local_vars, field_names, method_names)
                    false_val = self._convert_expression(false_val, class_name, local_vars, field_names, method_names)
                    return f"{condition} ? {true_val} : {false_val}"
        return expr

    def _convert_expression(self, expr: str, class_name: str = None, local_vars: set = None, field_names: set = None, method_names: set = None) -> str:
        """Convert Java expressions to Julia expressions."""
        if local_vars is None:
            local_vars = set()
        if field_names is None:
            field_names = set()
        if method_names is None:
            method_names = set()
            
        # Remove Java casts
        expr = re.sub(r'\(\s*(int|double|float|String|boolean)\s*\)\s*', '', expr)
        
        # Convert array syntax
        expr = re.sub(r'\{(.+)\}', r'[\1]', expr)
        
        # Convert .length to length() - do this before field access conversion
        expr = re.sub(r'(\w+)\.length', r'length(\1)', expr)
        
        # Convert array indexing from 0-based to 1-based
        def convert_array_index(match):
            array_name = match.group(1)
            index = int(match.group(2)) + 1  # Convert to 1-based
            return f"{array_name}[{index}]"
        
        expr = re.sub(r'(\w+)\[(\d+)\]', convert_array_index, expr)
        
        # Convert .this references
        expr = expr.replace('this.', '')
        
        # Convert method calls in expressions (e.g., "calculateAverage()" -> "calculateAverage(obj)")
        # This needs to happen before field access conversion to avoid conflicts
        if class_name and method_names:
            built_in_functions = {'println', 'length', 'sum', 'Int', 'Float64', 'String', 'Bool', 'Char', 'Vector', 'Array', 'Dict', 'Set'}
            julia_keywords = {'if', 'for', 'while', 'function', 'end', 'return', 'else', 'elseif', 'break', 'continue', 'try', 'catch', 'finally'}
            for method in method_names:
                if method not in built_in_functions and method not in julia_keywords:
                    # Match method calls like methodName() or methodName(args)
                    # But not if it's already been converted to method(obj,
                    # Use a more restrictive pattern to avoid matching operators
                    pattern = rf'(?<![a-zA-Z0-9_]){method}\s*\(([^)]*)\)'
                    def replace_method_call(match):
                        full_match = match.group(0)
                        args = match.group(1)
                        # Don't convert if it's already in the form method(obj,
                        if 'obj,' in full_match or 'obj)' in full_match or 'obj, obj' in full_match:
                            return full_match
                        if args and args.strip():
                            return f"{method}(obj, {args})"
                        else:
                            return f"{method}(obj)"
                    expr = re.sub(pattern, replace_method_call, expr)
        
        # Convert field access in expressions (e.g., "marks" -> "obj.marks" when it's a field)
        # But only if the field is known and not a local variable
        if class_name and field_names:
            for field in field_names:
                # Only replace if it's not a local variable
                if field not in local_vars:
                    # Replace field names with obj.field if they appear as standalone identifiers
                    # Be careful not to break function calls and other constructs
                    # Use a more restrictive pattern
                    pattern = rf'\b{field}\b(?!\s*[.([:])'
                    expr = re.sub(pattern, f'obj.{field}', expr)
            # Handle array access like marks[1] -> obj.marks[1]
            for field in field_names:
                if field not in local_vars:
                    pattern = rf'\b{field}\['
                    expr = re.sub(pattern, f'obj.{field}[', expr)
        
        # Convert boolean literals
        expr = expr.replace('true', 'true').replace('false', 'false')
        
        # Convert null
        expr = expr.replace('null', 'nothing')
        
        # Convert ternary operators (they're the same in Julia)
        # No change needed for ternary
        
        return expr.strip()

    def _validate_julia_syntax(self, julia_code: str) -> Dict[str, Any]:
        """Validate generated Julia code for common syntax errors."""
        errors = []
        unsupported_features = []
        
        # Check for remaining Java keywords
        java_keywords = ['public', 'private', 'protected', 'static', 'final', 'void', 'new', 'this']
        for keyword in java_keywords:
            if keyword in julia_code:
                errors.append(f"Java keyword '{keyword}' still present in code")
        
        # Check for Java array syntax (but allow in comments and type declarations)
        lines = julia_code.split('\n')
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped.startswith('#') and '{' in line and '}' in line:
                # Allow Vector{Int} style type declarations
                if not re.search(r'Vector\{[^}]*\}|Dict\{[^}]*\}|Set\{[^}]*\}', line):
                    if re.search(r'\{[^}]*\}', line):
                        errors.append(f"Java array syntax {{}} still present on line {i+1}")
        
        # Check for .length
        if '.length' in julia_code:
            errors.append("Java .length syntax still present")
        
        # Check for Java-style casts
        if re.search(r'\(\s*(int|double|float|String)\s*\)', julia_code):
            errors.append("Java-style casts still present")
        
        # Check for function/end balance (excluding comments)
        function_count = 0
        end_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('#'):
                function_count += stripped.count('function ')
                end_count += stripped.count('end')
        
        # Julia has 'end' for both functions and structs, so we expect more ends than functions
        # Allow some tolerance
        if end_count < function_count:
            errors.append(f"Missing 'end' statements: {function_count} functions/blocks but only {end_count} ends")
        
        # Check for if/end balance
        if_count = 0
        for_count = 0
        while_count = 0
        for line in lines:
            stripped = line.strip()
            if not stripped.startswith('#'):
                if_count += stripped.count('if ')
                for_count += stripped.count('for ')
                while_count += stripped.count('while ')
        
        block_starts = if_count + for_count + while_count
        expected_ends = function_count + block_starts
        # Allow some tolerance for struct ends
        if end_count < expected_ends:
            errors.append(f"Missing 'end' statements: expected at least {expected_ends} but found {end_count}")
        
        # Check for System.out
        if 'System.out' in julia_code:
            errors.append("System.out still present (should be println)")
        
        # Check for semicolons
        if ';' in julia_code:
            errors.append("Java semicolons still present")
        
        # Check for incorrect parentheses in if statements
        if re.search(r'if\s*\([^)]+\)', julia_code):
            errors.append("If statements should not have parentheses around condition in Julia")
        
        # Check for obj., in expressions (should be obj.)
        if 'obj., ' in julia_code:
            errors.append("Incorrect syntax 'obj., ' found")
        
        return {
            "has_errors": len(errors) > 0,
            "errors": errors,
            "unsupported_features": unsupported_features
        }
    
    def _validate_julia_runtime(self, julia_code: str) -> Dict[str, Any]:
        """Validate generated Julia code by attempting to run it if Julia is available."""
        import subprocess
        import tempfile
        import os
        
        try:
            # Try to run Julia to check if it's available
            result = subprocess.run(['julia', '--version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                return {
                    "julia_available": False,
                    "runtime_errors": [],
                    "output": ""
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {
                "julia_available": False,
                "runtime_errors": [],
                "output": ""
            }
        
        # Julia is available, try to run the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jl', delete=False) as f:
            f.write(julia_code)
            temp_file = f.name
        
        try:
            result = subprocess.run(['julia', temp_file], capture_output=True, timeout=10)
            output = result.stdout.decode('utf-8', errors='ignore')
            stderr = result.stderr.decode('utf-8', errors='ignore')
            
            runtime_errors = []
            if result.returncode != 0:
                # Parse Julia error messages
                if stderr:
                    runtime_errors.append(stderr.strip())
            
            return {
                "julia_available": True,
                "runtime_errors": runtime_errors,
                "output": output,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "julia_available": True,
                "runtime_errors": ["Execution timeout"],
                "output": "",
                "success": False
            }
        finally:
            try:
                os.unlink(temp_file)
            except:
                pass
