```mermaid
sequenceDiagram
    participant Developer
    participant CodeReview
    participant CI
    participant Deploy

    Developer->>CodeReview: Submit PR
    CodeReview->>Developer: Review Code
    Developer->>CodeReview: Address Feedback
    CodeReview->>CI: Run Tests
    CI->>CodeReview: Test Results
    CodeReview->>Deploy: Merge PR
    Deploy->>User: Deploy to Production
```