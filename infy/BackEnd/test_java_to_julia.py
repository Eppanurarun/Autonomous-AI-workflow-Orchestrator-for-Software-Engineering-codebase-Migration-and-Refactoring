"""Test Java to Julia conversion."""

import sys
sys.path.insert(0, '.')

from app.services.agents.migration.java_to_julia_agent import JavaToJuliaAgent

# Test Java code
java_code = """
public class StudentAnalyzer {
    private String name;
    private int[] marks;

    public StudentAnalyzer(String name, int[] marks) {
        this.name = name;
        this.marks = marks;
    }

    public double calculateAverage() {
        int total = 0;
        for (int mark : marks) {
            total += mark;
        }
        return (double) total / marks.length;
    }

    public int findHighest() {
        int highest = marks[0];
        for (int mark : marks) {
            if (mark > highest) {
                highest = mark;
            }
        }
        return highest;
    }

    public boolean hasPassed() {
        return calculateAverage() >= 40.0;
    }

    public void displayResult() {
        System.out.println("Student: " + name);
        System.out.println("Average: " + calculateAverage());
        System.out.println("Highest Mark: " + findHighest());
        System.out.println("Status: " + (hasPassed() ? "PASS" : "FAIL"));
    }

    public static void main(String[] args) {
        int[] marks = {85, 72, 91, 68, 79};

        StudentAnalyzer student = new StudentAnalyzer("Arun", marks);

        student.displayResult();
    }
}
"""

# Test conversion
agent = JavaToJuliaAgent()

# First, let's test the parsing
parsed = agent._parse_java_structure(java_code)
print("=== Parsed Structure ===")
print(f"Class: {parsed['class']}")
print(f"Fields: {parsed['fields']}")
print(f"Constructors: {parsed['constructors']}")
print(f"Methods: {[m['name'] for m in parsed['methods']]}")
print(f"Main: {parsed['main_method']}")

# Test expression conversion
print("\n=== Testing expression conversion ===")
test_expr = "(double) total / marks.length"
field_names = {field['name'] for field in parsed['fields']}
converted_expr = agent._convert_expression(test_expr, parsed['class']['name'], set(), field_names)
print(f"Expression: '{test_expr}' -> '{converted_expr}'")

# Test return statement processing
print("\n=== Testing return statement ===")
return_line = "return (double) total / marks.length;"
print(f"Original return line: '{return_line}'")
print(f"After stripping: '{return_line.strip()}'")
print(f"After rstrip semicolon: '{return_line.strip().rstrip(';')}'")
print(f"After startswith check: '{return_line.strip().rstrip(';')}'")
print(f"Substring after 'return ': '{return_line.strip().rstrip(';')[7:]}'")
method_names = {m['name'] for m in parsed['methods']}
return_converted = agent._convert_method_body_line(return_line, parsed['class']['name'], set(), field_names, method_names)
print(f"Return line: '{return_line}' -> '{return_converted}'")

# Test method body conversion for calculateAverage
print("\n=== Testing calculateAverage method body ===")
calc_avg_method = parsed['methods'][0]
print(f"Method body lines: {calc_avg_method['body']}")

# Test each line conversion
print("\n=== Testing individual line conversions ===")
method_names = {m['name'] for m in parsed['methods']}
for line in calc_avg_method['body']:
    converted = agent._convert_method_body_line(line, parsed['class']['name'], set(), field_names, method_names)
    print(f"Line: '{line.strip()}' -> '{converted}'")

# Test findHighest method body
print("\n=== Testing findHighest method body ===")
find_highest_method = parsed['methods'][1]
print(f"Method body lines: {find_highest_method['body']}")
for line in find_highest_method['body']:
    converted = agent._convert_method_body_line(line, parsed['class']['name'], set(), field_names, method_names)
    print(f"Line: '{line.strip()}' -> '{converted}'")

# Test if statement conversion specifically
print("\n=== Testing if statement conversion ===")
if_line = "if (mark > highest) {"
condition = "mark > highest"
converted_condition = agent._convert_expression(condition, parsed['class']['name'], set(), field_names, method_names)
print(f"Condition: '{condition}' -> '{converted_condition}'")

# Test println content conversion
print("\n=== Testing println content conversion ===")
println_content = '"Average: " + calculateAverage()'
converted_content = agent._convert_expression(println_content, parsed['class']['name'], set(), field_names, method_names)
print(f"Content: '{println_content}' -> '{converted_content}'")

print("\n=== Generated Julia Code ===")
result = agent.convert(java_code)
print(result.get("julia_code", ""))
print("\n=== Conversion Notes ===")
print(result.get("conversion_notes", []))
print("\n=== Errors ===")
print(result.get("error", "None"))
