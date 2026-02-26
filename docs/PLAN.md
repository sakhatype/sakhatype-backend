# Sakhatype — Project Plan

## What It Does

**Sakhatype** is a high-performance backend for a typing speed application. It manages user progression through an experience-based leveling system, tracks detailed typing metrics (WPM, accuracy, consistency), and serves randomized word sets for practice. It features a competitive leaderboard system and provides comprehensive profile statistics.

## Access Control

The API uses **OAuth2 with Password Flow and JWT (JSON Web Tokens)**.

- **Public Endpoints:** Registration, Login, Leaderboards, and Word generation.
- **Protected Endpoints:** Saving test results and retrieving the "Me" profile require a valid `Bearer` token in the Authorization header.
- **Security:** Passwords are encrypted using the **Argon2** hashing algorithm.

## User Flow

1. **Registration/Login**: User creates an account or authenticates to receive a JWT.
2. **Practice**: Client fetches random words via `/api/words`.
3. **Submission**: Upon completing a test, the client posts results to `/api/results`.
4. **Progression**: The backend updates the user's total XP, Level, and Best WPM.
5. **Competition**: Users view their standing on the WPM or Accuracy leaderboards.

## API Endpoints

| Category     | Endpoint                       | Method | Description                               |
| :----------- | :----------------------------- | :----- | :---------------------------------------- |
| **Auth**     | `/api/auth/register`           | `POST` | Create a new account                      |
| **Auth**     | `/api/auth/login`              | `POST` | Get JWT token (OAuth2 form)               |
| **User**     | `/api/users/me`                | `GET`  | Get current authenticated user profile    |
| **User**     | `/api/profile/{username}`      | `GET`  | Get public profile stats of any user      |
| **Results**  | `/api/results`                 | `POST` | Save test result and update user XP/Level |
| **Results**  | `/api/results/user/{username}` | `GET`  | Get recent test history for a user        |
| **Words**    | `/api/words`                   | `GET`  | Get a list of random words for the test   |
| **Rankings** | `/api/leaderboard/wpm`         | `GET`  | Get top users by Words Per Minute         |
| **Rankings** | `/api/leaderboard/accuracy`    | `GET`  | Get top users by Accuracy %               |

## Progression System

The backend includes a built-in leveling logic:

- **Experience (XP):** Calculated as `WPM + Accuracy` per test.
- **Leveling:** Users gain 1 level for every **1,000 XP** earned.
- **Stat Tracking:** The system automatically tracks "Lifetime" stats including total tests and total time spent typing.

## Configuration

Configured via environment variables (loaded from `.env`):

| Variable                      | Required | Default | Description                           |
| :---------------------------- | :------- | :------ | :------------------------------------ |
| `DATABASE_URL`                | Yes      | —       | Connection string (PostgreSQL/SQLite) |
| `SECRET_KEY`                  | Yes      | —       | Key for signing JWT tokens            |
| `ALGORITHM`                   | No       | `HS256` | JWT signing algorithm                 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No       | `30`    | Token validity duration               |
| `ALLOWED_ORIGINS`             | Yes      | —       | CORS whitelist (comma-separated)      |
