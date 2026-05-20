# Debrief

Answer these after completing the implementation.

1. What workflow state transition was unsafe in the starter, and why?
2. How does your implementation prevent duplicate external starts under retry?
3. How does the reconciler decide whether local DB state or external service truth wins?
4. What operator action should be taken when external truth is unknown?
5. How did you make repeated sweeper or reconciler runs idempotent?

