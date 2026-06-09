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
