# Module and Lesson Endpoints - Complete Documentation

## Overview

Comprehensive REST API endpoints for managing modules, lessons, and user progress tracking.

## Modules Endpoints

### Base Path: `/api/v1/modules`

#### 1. Get Modules by Course
```
GET /api/v1/modules?course_id={course_id}&page={page}&per_page={per_page}
```

**Query Parameters:**
- `course_id` (required): ID of the course
- `page` (optional, default: 1): Page number
- `per_page` (optional, default: 100, max: 100): Items per page

**Authentication:** Not required for public courses

**Response:**
```json
{
  "success": true,
  "data": {
    "modules": [...],
    "page": 1,
    "per_page": 100,
    "total": 5
  },
  "details": "Retrieved 5 module(s)"
}
```

---

#### 2. Get Module by ID
```
GET /api/v1/modules/{module_id}
```

**Authentication:** Not required for public courses

---

#### 3. Create Module
```
POST /api/v1/modules
```

**Authentication:** Required

**Request Body:**
```json
{
  "course_id": 1,
  "title": "Introduction to Python",
  "module_slug": "intro-python",
  "description": "Learn Python basics",
  "objectives": ["Understand variables", "Learn functions"],
  "order": 0
}
```

---

#### 4. Update Module
```
PATCH /api/v1/modules/{module_id}
```

**Authentication:** Required

**Request Body:** (all fields optional)
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "order": 1
}
```

---

#### 5. Delete Module
```
DELETE /api/v1/modules/{module_id}
```

**Authentication:** Required

---

### User Module Progress Endpoints

#### 6. Start Module
```
POST /api/v1/modules/start
```

**Authentication:** Required

**Request Body:**
```json
{
  "module_id": 1,
  "course_id": 1,
  "status": "in_progress"
}
```

**Description:** Creates a user module progress record when a user starts a module.

---

#### 7. Get User Modules
```
GET /api/v1/modules/user/modules?course_id={course_id}
```

**Query Parameters:**
- `course_id` (required): ID of the course

**Authentication:** Required

**Description:** Get all user module progress records for a specific course.

---

#### 8. Get User Module Detail
```
GET /api/v1/modules/user/modules/detail?module_id={module_id}
```

**Query Parameters:**
- `module_id` (required): ID of the module

**Authentication:** Required

**Description:** Get user progress for a specific module.

---

#### 9. Update User Module
```
PATCH /api/v1/modules/user/modules/update?module_id={module_id}
```

**Query Parameters:**
- `module_id` (required): ID of the module

**Authentication:** Required

**Request Body:**
```json
{
  "status": "completed"
}
```

---

#### 10. Complete Module
```
POST /api/v1/modules/user/modules/complete?module_id={module_id}
```

**Query Parameters:**
- `module_id` (required): ID of the module

**Authentication:** Required

**Description:** Mark a module as completed.

---

## Lessons Endpoints

### Base Path: `/api/v1/lessons`

#### 1. Get Lessons
```
GET /api/v1/lessons?module_id={module_id}&page={page}&per_page={per_page}
GET /api/v1/lessons?course_id={course_id}&page={page}&per_page={per_page}
```

**Query Parameters:**
- `module_id` OR `course_id` (one required): Filter by module or course
- `page` (optional, default: 1): Page number
- `per_page` (optional, default: 100, max: 100): Items per page

**Authentication:** Not required for public courses

---

#### 2. Get Lesson by ID
```
GET /api/v1/lessons/{lesson_id}
```

**Authentication:** Not required for public courses

---

#### 3. Create Lesson
```
POST /api/v1/lessons
```

**Authentication:** Required

**Request Body:**
```json
{
  "module_id": 1,
  "course_id": 1,
  "title": "Variables and Data Types",
  "description": "Learn about Python variables",
  "objectives": ["Understand variables", "Learn data types"],
  "content": "# Lesson Content\n\nMarkdown content here...",
  "audio_transcript_url": "https://example.com/audio.mp3",
  "has_quiz": true,
  "credit_cost": 10,
  "audio_credit_cost": 5,
  "order": 0
}
```

---

#### 4. Update Lesson
```
PATCH /api/v1/lessons/{lesson_id}
```

**Authentication:** Required

**Request Body:** (all fields optional)
```json
{
  "title": "Updated Title",
  "content": "Updated content",
  "credit_cost": 15
}
```

---

#### 5. Delete Lesson
```
DELETE /api/v1/lessons/{lesson_id}
```

**Authentication:** Required

---

### User Lesson Progress Endpoints

#### 6. Start Lesson
```
POST /api/v1/lessons/start
```

**Authentication:** Required

**Request Body:**
```json
{
  "lesson_id": 1,
  "module_id": 1,
  "course_id": 1,
  "status": "in_progress"
}
```

---

#### 7. Get User Lessons
```
GET /api/v1/lessons/user/lessons?module_id={module_id}
GET /api/v1/lessons/user/lessons?course_id={course_id}
```

**Query Parameters:**
- `module_id` OR `course_id` (one required): Filter by module or course

**Authentication:** Required

---

#### 8. Get User Lesson Detail
```
GET /api/v1/lessons/user/lessons/detail?lesson_id={lesson_id}
```

**Query Parameters:**
- `lesson_id` (required): ID of the lesson

**Authentication:** Required

---

#### 9. Update User Lesson
```
PATCH /api/v1/lessons/user/lessons/update?lesson_id={lesson_id}
```

**Query Parameters:**
- `lesson_id` (required): ID of the lesson

**Authentication:** Required

**Request Body:** (all fields optional)
```json
{
  "is_unlocked": true,
  "is_lesson_unlocked": true,
  "is_audio_unlocked": true,
  "is_quiz_completed": true,
  "status": "completed"
}
```

---

#### 10. Unlock Lesson
```
POST /api/v1/lessons/user/lessons/unlock?lesson_id={lesson_id}
```

**Query Parameters:**
- `lesson_id` (required): ID of the lesson

**Authentication:** Required

**Description:** Unlock a lesson for the current user.

---

#### 11. Unlock Audio
```
POST /api/v1/lessons/user/lessons/unlock-audio?lesson_id={lesson_id}
```

**Query Parameters:**
- `lesson_id` (required): ID of the lesson

**Authentication:** Required

**Description:** Unlock audio for a lesson (requires credits).

---

#### 12. Complete Quiz
```
POST /api/v1/lessons/user/lessons/complete-quiz?lesson_id={lesson_id}
```

**Query Parameters:**
- `lesson_id` (required): ID of the lesson

**Authentication:** Required

**Description:** Mark quiz as completed for a lesson.

---

#### 13. Complete Lesson
```
POST /api/v1/lessons/user/lessons/complete?lesson_id={lesson_id}
```

**Query Parameters:**
- `lesson_id` (required): ID of the lesson

**Authentication:** Required

**Description:** Mark a lesson as completed.

---

## Data Models

### Module
```typescript
{
  id: number;
  course_id: number;
  title: string;
  module_slug: string;
  description?: string;
  objectives?: string[];
  order: number;
  created_at: datetime;
  updated_at?: datetime;
}
```

### UserModule
```typescript
{
  id: number;
  user_id: number;
  course_id: number;
  module_id: number;
  status: "in_progress" | "completed";
  created_at: datetime;
  updated_at?: datetime;
}
```

### Lesson
```typescript
{
  id: number;
  module_id: number;
  course_id: number;
  title: string;
  description?: string;
  objectives?: string[];
  content?: string;  // Markdown
  audio_transcript_url?: string;
  has_quiz: boolean;
  credit_cost: number;
  audio_credit_cost: number;
  order: number;
  created_at: datetime;
  updated_at?: datetime;
}
```

### UserLesson
```typescript
{
  id: number;
  user_id: number;
  course_id: number;
  module_id: number;
  lesson_id: number;
  is_unlocked: boolean;
  is_lesson_unlocked: boolean;
  is_audio_unlocked: boolean;
  is_quiz_completed: boolean;
  status: "in_progress" | "completed";
  created_at: datetime;
  updated_at?: datetime;
}
```

---

## Progress Tracking Flow

### Typical User Journey

1. **Enroll in Course**
   ```
   POST /api/v1/courses/{course_id}/enroll
   ```

2. **Start First Module**
   ```
   POST /api/v1/modules/start
   Body: { module_id: 1, course_id: 1 }
   ```

3. **Start First Lesson**
   ```
   POST /api/v1/lessons/start
   Body: { lesson_id: 1, module_id: 1, course_id: 1 }
   ```

4. **Unlock Lesson Content** (if required)
   ```
   POST /api/v1/lessons/user/lessons/unlock?lesson_id=1
   ```

5. **Complete Quiz** (if available)
   ```
   POST /api/v1/lessons/user/lessons/complete-quiz?lesson_id=1
   ```

6. **Complete Lesson**
   ```
   POST /api/v1/lessons/user/lessons/complete?lesson_id=1
   ```

7. **Complete Module** (after all lessons)
   ```
   POST /api/v1/modules/user/modules/complete?module_id=1
   ```

---

## Error Responses

All endpoints return standard error responses:

```json
{
  "success": false,
  "data": null,
  "details": "Error message here"
}
```

**Common HTTP Status Codes:**
- `200 OK`: Success
- `400 Bad Request`: Invalid input or duplicate record
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

---

## Testing with Swagger UI

Access the interactive API documentation at:
```
http://localhost:8000/docs
```

All endpoints are documented with:
- Request/response schemas
- Example values
- Try-it-out functionality
- Authentication requirements

---

## Summary

**Total Endpoints Created:**
- **Modules:** 10 endpoints (5 CRUD + 5 user progress)
- **Lessons:** 13 endpoints (5 CRUD + 8 user progress)

**Features:**
- ✅ Full CRUD operations for modules and lessons
- ✅ User progress tracking
- ✅ Unique constraints prevent duplicate records
- ✅ Query parameter-based filtering
- ✅ Pagination support
- ✅ Comprehensive error handling
- ✅ Type-safe with Pydantic validation
