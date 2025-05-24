# exercise_manager.py
import json
from datetime import datetime
from models import db, Exercise, ExerciseProgress, User

def create_exercise(title, description, difficulty, category, initial_code, solution_code, test_cases):
    """
    Create a new exercise in the database
    
    Args:
        title: Exercise title
        description: Exercise description (HTML allowed)
        difficulty: Difficulty level ('easy', 'medium', 'hard')
        category: Category name
        initial_code: Initial code provided to user
        solution_code: Solution code
        test_cases: List of test cases (dict with 'input' and 'expected_output')
    
    Returns:
        The created Exercise object
    """
    # Validate difficulty
    if difficulty not in ['easy', 'medium', 'hard']:
        raise ValueError("Difficulty must be one of: 'easy', 'medium', 'hard'")
    
    # Convert test_cases to JSON
    test_cases_json = json.dumps(test_cases)
    
    exercise = Exercise(
        title=title,
        description=description,
        difficulty=difficulty,
        category=category,
        initial_code=initial_code,
        solution_code=solution_code,
        test_cases=test_cases_json
    )
    
    db.session.add(exercise)
    db.session.commit()
    
    return exercise

def get_all_exercises():
    """
    Get all exercises
    
    Returns:
        List of Exercise objects
    """
    return Exercise.query.all()

def get_exercise_by_id(exercise_id):
    """
    Get exercise by ID
    
    Args:
        exercise_id: Exercise ID
    
    Returns:
        Exercise object or None if not found
    """
    return Exercise.query.get(exercise_id)

def get_exercises_by_difficulty(difficulty):
    """
    Get exercises by difficulty level
    
    Args:
        difficulty: Difficulty level ('easy', 'medium', 'hard')
    
    Returns:
        List of Exercise objects
    """
    return Exercise.query.filter_by(difficulty=difficulty).all()

def get_exercises_by_category(category):
    """
    Get exercises by category
    
    Args:
        category: Category name
    
    Returns:
        List of Exercise objects
    """
    return Exercise.query.filter_by(category=category).all()

def get_user_progress(user_id, exercise_id=None):
    """
    Get user progress on exercises
    
    Args:
        user_id: User ID
        exercise_id: Optional exercise ID to get progress for a specific exercise
    
    Returns:
        Dictionary mapping exercise_id to ExerciseProgress objects if exercise_id is None,
        or a single ExerciseProgress object if exercise_id is provided
    """
    if exercise_id:
        return ExerciseProgress.query.filter_by(
            user_id=user_id,
            exercise_id=exercise_id
        ).first()
    
    progress_items = ExerciseProgress.query.filter_by(user_id=user_id).all()
    progress_dict = {item.exercise_id: item for item in progress_items}
    return progress_dict

def get_or_create_progress(user_id, exercise_id):
    """
    Get or create progress for a user on an exercise
    
    Args:
        user_id: User ID
        exercise_id: Exercise ID
    
    Returns:
        ExerciseProgress object
    """
    progress = ExerciseProgress.query.filter_by(
        user_id=user_id,
        exercise_id=exercise_id
    ).first()
    
    if not progress:
        exercise = get_exercise_by_id(exercise_id)
        if not exercise:
            raise ValueError(f"Exercise with ID {exercise_id} not found")
        
        progress = ExerciseProgress(
            user_id=user_id,
            exercise_id=exercise_id,
            status='not_started',
            user_code=exercise.initial_code
        )
        db.session.add(progress)
        db.session.commit()
    
    return progress

def update_progress(user_id, exercise_id, status=None, user_code=None, increment_attempts=False, completed=False):
    """
    Update user progress on an exercise
    
    Args:
        user_id: User ID
        exercise_id: Exercise ID
        status: Optional new status ('not_started', 'in_progress', 'completed')
        user_code: Optional updated user code
        increment_attempts: Whether to increment the attempts counter
        completed: Whether to mark the exercise as completed
    
    Returns:
        Updated ExerciseProgress object
    """
    progress = get_or_create_progress(user_id, exercise_id)
    
    if status:
        progress.status = status
    
    if user_code is not None:
        progress.user_code = user_code
    
    if increment_attempts:
        progress.attempts += 1
        progress.last_attempt = datetime.utcnow()
    
    if completed and progress.status != 'completed':
        progress.status = 'completed'
        progress.completed_at = datetime.utcnow()
    
    db.session.commit()
    return progress

def get_user_statistics(user_id):
    """
    Get statistics about user's exercise progress
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary with statistics
    """
    # Get user
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")
    
    # Get all exercises and user progress
    all_exercises = get_all_exercises()
    progress_dict = get_user_progress(user_id)
    
    # Count by status
    total = len(all_exercises)
    completed = 0
    in_progress = 0
    not_started = 0
    
    # Count by difficulty
    easy_total = 0
    easy_completed = 0
    medium_total = 0
    medium_completed = 0
    hard_total = 0
    hard_completed = 0
    
    for exercise in all_exercises:
        progress = progress_dict.get(exercise.id)
        
        # Count by difficulty
        if exercise.difficulty == 'easy':
            easy_total += 1
            if progress and progress.status == 'completed':
                easy_completed += 1
        elif exercise.difficulty == 'medium':
            medium_total += 1
            if progress and progress.status == 'completed':
                medium_completed += 1
        elif exercise.difficulty == 'hard':
            hard_total += 1
            if progress and progress.status == 'completed':
                hard_completed += 1
        
        # Count by status
        if progress:
            if progress.status == 'completed':
                completed += 1
            elif progress.status == 'in_progress':
                in_progress += 1
            else:
                not_started += 1
        else:
            not_started += 1
    
    return {
        'total': total,
        'completed': completed,
        'in_progress': in_progress,
        'not_started': not_started,
        'completion_rate': round(completed / total * 100, 1) if total > 0 else 0,
        'easy': {
            'total': easy_total,
            'completed': easy_completed,
            'completion_rate': round(easy_completed / easy_total * 100, 1) if easy_total > 0 else 0
        },
        'medium': {
            'total': medium_total,
            'completed': medium_completed,
            'completion_rate': round(medium_completed / medium_total * 100, 1) if medium_total > 0 else 0
        },
        'hard': {
            'total': hard_total,
            'completed': hard_completed,
            'completion_rate': round(hard_completed / hard_total * 100, 1) if hard_total > 0 else 0
        }
    }

def create_sample_exercises():
    """
    Create sample exercises for testing
    """
    # Check if exercises already exist
    if Exercise.query.count() > 0:
        return
    
    # Create sample exercises
    exercises = [
        {
            'title': 'Hello, World!',
            'description': """<p>Write a C program that prints "Hello, World!" to the console.</p>
            <p>This is a classic first program that helps verify your environment is set up correctly.</p>""",
            'difficulty': 'easy',
            'category': 'Basics',
            'initial_code': """#include <stdio.h>

int main() {
    // Write your code here
    
    return 0;
}""",
            'solution_code': r"""#include <stdio.h>

int main() {
    printf("Hello, World!\\n");
    return 0;
}""",
            'test_cases': [
                {
                    'input': '',
                    'expected_output': 'Hello, World!'
                }
            ]
        },
        {
            'title': 'Sum of Two Numbers',
            'description': """<p>Write a C program that takes two integers as input and prints their sum.</p>
            <p>Input format: Two integers separated by a space</p>
            <p>Output format: A single integer representing the sum</p>""",
            'difficulty': 'easy',
            'category': 'Basics',
            'initial_code': """#include <stdio.h>

int main() {
    int num1, num2, sum;
    
    // Read two integers
    
    // Calculate the sum
    
    // Print the result
    
    return 0;
}""",
            'solution_code': """#include <stdio.h>

int main() {
    int num1, num2, sum;
    
    // Read two integers
    scanf("%d %d", &num1, &num2);
    
    // Calculate the sum
    sum = num1 + num2;
    
    // Print the result
    printf("%d", sum);
    
    return 0;
}""",
            'test_cases': [
                {
                    'input': '5 7',
                    'expected_output': '12'
                },
                {
                    'input': '-3 8',
                    'expected_output': '5'
                },
                {
                    'input': '0 0',
                    'expected_output': '0'
                }
            ]
        },
        {
            'title': 'Factorial Calculation',
            'description': """<p>Write a C program that calculates the factorial of a given number.</p>
            <p>The factorial of a non-negative integer n is the product of all positive integers less than or equal to n.</p>
            <p>For example, factorial of 5 (denoted as 5!) = 5 × 4 × 3 × 2 × 1 = 120</p>
            <p>Input: A single non-negative integer n</p>
            <p>Output: The factorial of n</p>""",
            'difficulty': 'medium',
            'category': 'Loops',
            'initial_code': """#include <stdio.h>

int main() {
    int n;
    unsigned long long factorial = 1;
    
    // Read the input
    scanf("%d", &n);
    
    // Calculate factorial
    // Write your code here
    
    // Print the result
    printf("%llu", factorial);
    
    return 0;
}""",
            'solution_code': """#include <stdio.h>

int main() {
    int n;
    unsigned long long factorial = 1;
    
    // Read the input
    scanf("%d", &n);
    
    // Calculate factorial
    for(int i = 1; i <= n; i++) {
        factorial *= i;
    }
    
    // Print the result
    printf("%llu", factorial);
    
    return 0;
}""",
            'test_cases': [
                {
                    'input': '5',
                    'expected_output': '120'
                },
                {
                    'input': '0',
                    'expected_output': '1'
                },
                {
                    'input': '10',
                    'expected_output': '3628800'
                }
            ]
        },
        {
            'title': 'Reverse an Array',
            'description': """<p>Write a C program to reverse an array of integers.</p>
            <p>Input format:</p>
            <ul>
                <li>The first line contains an integer n, representing the number of elements in the array.</li>
                <li>The second line contains n space-separated integers.</li>
            </ul>
            <p>Output format: n space-separated integers representing the reversed array.</p>""",
            'difficulty': 'medium',
            'category': 'Arrays',
            'initial_code': """#include <stdio.h>

int main() {
    int n;
    
    // Read the number of elements
    scanf("%d", &n);
    
    int arr[n];
    
    // Read the array elements
    for(int i = 0; i < n; i++) {
        scanf("%d", &arr[i]);
    }
    
    // Reverse the array
    // Write your code here
    
    // Print the reversed array
    for(int i = 0; i < n; i++) {
        printf("%d", arr[i]);
        if(i < n - 1) printf(" ");
    }
    
    return 0;
}""",
            'solution_code': """#include <stdio.h>

int main() {
    int n;
    
    // Read the number of elements
    scanf("%d", &n);
    
    int arr[n];
    
    // Read the array elements
    for(int i = 0; i < n; i++) {
        scanf("%d", &arr[i]);
    }
    
    // Reverse the array
    for(int i = 0; i < n/2; i++) {
        int temp = arr[i];
        arr[i] = arr[n-i-1];
        arr[n-i-1] = temp;
    }
    
    // Print the reversed array
    for(int i = 0; i < n; i++) {
        printf("%d", arr[i]);
        if(i < n - 1) printf(" ");
    }
    
    return 0;
}""",
            'test_cases': [
                {
                    'input': '5\n1 2 3 4 5',
                    'expected_output': '5 4 3 2 1'
                },
                {
                    'input': '3\n10 20 30',
                    'expected_output': '30 20 10'
                },
                {
                    'input': '1\n42',
                    'expected_output': '42'
                }
            ]
        },
        {
            'title': 'Binary Search',
            'description': """<p>Implement the binary search algorithm in C.</p>
            <p>Binary search is an efficient algorithm for finding an item in a sorted array.</p>
            <p>Input format:</p>
            <ul>
                <li>The first line contains two integers: n (the number of elements in the array) and x (the target value to search for).</li>
                <li>The second line contains n space-separated integers in ascending order.</li>
            </ul>
            <p>Output format: The index of the target value in the array (0-indexed), or -1 if the target is not found.</p>""",
            'difficulty': 'hard',
            'category': 'Algorithms',
            'initial_code': """#include <stdio.h>

int binarySearch(int arr[], int n, int x) {
    // Implement binary search algorithm
    // Return the index of x if found, or -1 if not found
    
    return -1;
}

int main() {
    int n, x;
    
    // Read n and x
    scanf("%d %d", &n, &x);
    
    int arr[n];
    
    // Read the sorted array
    for(int i = 0; i < n; i++) {
        scanf("%d", &arr[i]);
    }
    
    // Search for x using binary search
    int result = binarySearch(arr, n, x);
    
    // Print the result
    printf("%d", result);
    
    return 0;
}""",
            'solution_code': """#include <stdio.h>

int binarySearch(int arr[], int n, int x) {
    int left = 0;
    int right = n - 1;
    
    while (left <= right) {
        int mid = left + (right - left) / 2;
        
        // Check if x is present at mid
        if (arr[mid] == x)
            return mid;
        
        // If x greater, ignore left half
        if (arr[mid] < x)
            left = mid + 1;
        
        // If x is smaller, ignore right half
        else
            right = mid - 1;
    }
    
    // If we reach here, element was not present
    return -1;
}

int main() {
    int n, x;
    
    // Read n and x
    scanf("%d %d", &n, &x);
    
    int arr[n];
    
    // Read the sorted array
    for(int i = 0; i < n; i++) {
        scanf("%d", &arr[i]);
    }
    
    // Search for x using binary search
    int result = binarySearch(arr, n, x);
    
    // Print the result
    printf("%d", result);
    
    return 0;
}""",
            'test_cases': [
                {
                    'input': '5 4\n1 2 3 4 5',
                    'expected_output': '3'
                },
                {
                    'input': '5 6\n1 2 3 4 5',
                    'expected_output': '-1'
                },
                {
                    'input': '10 7\n1 2 3 4 5 6 7 8 9 10',
                    'expected_output': '6'
                }
            ]
        }
    ]
    
    for exercise_data in exercises:
        create_exercise(
            title=exercise_data['title'],
            description=exercise_data['description'],
            difficulty=exercise_data['difficulty'],
            category=exercise_data['category'],
            initial_code=exercise_data['initial_code'],
            solution_code=exercise_data['solution_code'],
            test_cases=exercise_data['test_cases']
        )
    
    print(f"Created {len(exercises)} sample exercises")