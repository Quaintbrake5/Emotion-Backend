# TODO: Update API Base URLs

## Tasks
- [x] Rename API_BASE_URL to API_BASE_PUBLIC_URL in emotion-frontend/src/api/api.ts
- [x] Add API_BASE_LOCAL_URL constant in emotion-frontend/src/api/api.ts
- [x] Update baseURL usage in emotion-frontend/src/api/api.ts
- [x] Rename API_BASE_URL to API_BASE_PUBLIC_URL in emotion-frontend/src/services/audioService.ts
- [x] Add API_BASE_LOCAL_URL constant in emotion-frontend/src/services/audioService.ts
- [x] Update baseURL usage in emotion-frontend/src/services/audioService.ts
- [x] Implement automatic environment-based URL switching
- [x] Update refreshApi to use automatic URL switching

## Summary
All API base URL constants have been successfully updated. The frontend now automatically switches between local (http://localhost:8001) and public (https://emotion-backend-hxur.onrender.com/) URLs based on the development environment using `import.meta.env.DEV`. This eliminates the need to manually change URLs when switching between development and production.
