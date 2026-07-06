# Security Notes

This utility processes Okta user export data. User exports may contain personal information and should be handled as sensitive internal data.

- Do not commit real user exports to Git.
- Do not share output folders that contain production user data.
- Use test data for development and demonstrations.
- Review `.gitignore` before adding this utility to a repository.
- This utility is local-only by default and does not require API tokens.
