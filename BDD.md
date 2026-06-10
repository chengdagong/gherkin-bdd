# BDD Requirements

All user-facing functionality in this project must be described by a Gherkin feature file.

Feature files use the `.feature` extension and are the source of truth for application behavior. Product requirements, implementation plans, UI changes, test code, and agent instructions must align with the relevant `.feature` files.

When adding or changing functionality:

- Create or update the matching `.feature` file before implementation.
- Describe observable behavior in Gherkin, not internal implementation details.
- Treat `Feature`, `Rule`, `Scenario`, `Given`, `When`, and `Then` wording as product language.
- Keep step definitions, mocks, selectors, database fields, and test helper names out of the `.feature` file unless they are part of the product behavior.
- If code and a `.feature` file disagree, update the `.feature` file first or explicitly call out the product decision that changes it.
- Do not mark work complete until the implemented behavior matches the relevant `.feature` file.

## Implementation workflow

Every feature implementation follows red-green order:

1. Write or update the `.feature` file first.
2. Build automated tests from its scenarios.
3. Run the tests and confirm they all fail. A test that passes before the implementation exists does not verify the new behavior — rewrite it.
4. Write the implementation.
5. Run the tests again, debugging and fixing until all of them pass.

Do not start implementing before step 3, and do not mark work complete before step 5.
