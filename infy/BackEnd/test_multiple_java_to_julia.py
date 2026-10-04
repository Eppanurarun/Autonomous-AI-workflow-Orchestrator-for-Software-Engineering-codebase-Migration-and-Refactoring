"""Test Java to Julia conversion with multiple examples."""

import sys
sys.path.insert(0, '.')

from app.services.agents.migration.java_to_julia_agent import JavaToJuliaAgent

# Test 1: StudentAnalyzer (the original example)
java_code_1 = """
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

# Test 2: Simple Calculator
java_code_2 = """
public class Calculator {
    private double result;

    public Calculator() {
        this.result = 0.0;
    }

    public void add(double value) {
        this.result += value;
    }

    public void subtract(double value) {
        this.result -= value;
    }

    public void multiply(double value) {
        this.result *= value;
    }

    public void divide(double value) {
        if (value != 0) {
            this.result /= value;
        }
    }

    public double getResult() {
        return this.result;
    }

    public void clear() {
        this.result = 0.0;
    }

    public static void main(String[] args) {
        Calculator calc = new Calculator();
        calc.add(10.0);
        calc.multiply(5.0);
        calc.subtract(3.0);
        calc.divide(2.0);
        System.out.println("Result: " + calc.getResult());
    }
}
"""

# Test 3: Array manipulation
java_code_3 = """
public class ArrayOperations {
    public static int findMax(int[] arr) {
        int max = arr[0];
        for (int i = 1; i < arr.length; i++) {
            if (arr[i] > max) {
                max = arr[i];
            }
        }
        return max;
    }

    public static int findMin(int[] arr) {
        int min = arr[0];
        for (int i = 1; i < arr.length; i++) {
            if (arr[i] < min) {
                min = arr[i];
            }
        }
        return min;
    }

    public static int sumArray(int[] arr) {
        int sum = 0;
        for (int num : arr) {
            sum += num;
        }
        return sum;
    }

    public static void main(String[] args) {
        int[] numbers = {10, 5, 20, 8, 15};
        System.out.println("Max: " + findMax(numbers));
        System.out.println("Min: " + findMin(numbers));
        System.out.println("Sum: " + sumArray(numbers));
    }
}
"""

# Test 4: String manipulation
java_code_4 = """
public class StringProcessor {
    private String text;

    public StringProcessor(String text) {
        this.text = text;
    }

    public int getLength() {
        return this.text.length();
    }

    public String toUpperCase() {
        return this.text.toUpperCase();
    }

    public String toLowerCase() {
        return this.text.toLowerCase();
    }

    public boolean contains(String substring) {
        return this.text.contains(substring);
    }

    public void displayInfo() {
        System.out.println("Original: " + this.text);
        System.out.println("Length: " + getLength());
        System.out.println("Upper: " + toUpperCase());
        System.out.println("Lower: " + toLowerCase());
    }

    public static void main(String[] args) {
        StringProcessor processor = new StringProcessor("Hello World");
        processor.displayInfo();
    }
}
"""

# Test 5: Conditional logic
java_code_5 = """
public class GradeChecker {
    private int score;

    public GradeChecker(int score) {
        this.score = score;
    }

    public String getGrade() {
        if (score >= 90) {
            return "A";
        } else if (score >= 80) {
            return "B";
        } else if (score >= 70) {
            return "C";
        } else if (score >= 60) {
            return "D";
        } else {
            return "F";
        }
    }

    public boolean isPassing() {
        return score >= 60;
    }

    public void displayGrade() {
        System.out.println("Score: " + score);
        System.out.println("Grade: " + getGrade());
        System.out.println("Passing: " + (isPassing() ? "Yes" : "No"));
    }

    public static void main(String[] args) {
        GradeChecker checker = new GradeChecker(85);
        checker.displayGrade();
    }
}
"""

test_cases = [
    ("StudentAnalyzer", java_code_1),
    ("Calculator", java_code_2),
    ("ArrayOperations", java_code_3),
    ("StringProcessor", java_code_4),
    ("GradeChecker", java_code_5),
]

agent = JavaToJuliaAgent()

print("=" * 80)
print("Testing Java to Julia Conversion with Multiple Examples")
print("=" * 80)

for test_name, java_code in test_cases:
    print(f"\n{'=' * 80}")
    print(f"Test: {test_name}")
    print(f"{'=' * 80}")
    
    print("\n--- Original Java Code ---")
    print(java_code)
    
    result = agent.convert(java_code)
    
    print("\n--- Generated Julia Code ---")
    print(result.get("julia_code", ""))
    
    print("\n--- Conversion Notes ---")
    for note in result.get("conversion_notes", []):
        print(f"  - {note}")
    
    print("\n--- Validation Status ---")
    syntax_validation = result.get("syntax_validation", {})
    if syntax_validation.get("has_errors"):
        print("  Syntax Errors:")
        for error in syntax_validation.get("errors", []):
            print(f"    - {error}")
    else:
        print("  [OK] Syntax validation passed")
    
    runtime_validation = result.get("runtime_validation", {})
    if runtime_validation.get("julia_available"):
        if runtime_validation.get("success"):
            print("  [OK] Runtime validation passed")
            print(f"  Output: {runtime_validation.get('output', '')}")
        else:
            print("  Runtime Errors:")
            for error in runtime_validation.get("runtime_errors", []):
                print(f"    - {error}")
    else:
        print("  Runtime validation: Julia not available")
    
    if result.get("error"):
        print(f"\n--- Error ---")
        print(f"  {result.get('error')}")

print("\n" + "=" * 80)
print("Testing Complete")
print("=" * 80)
