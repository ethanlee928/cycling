# Cycling

Extract cycling workout data from Strava, analyse the performance using Strava API.

## 🖥️ Dependencies

### Python Environment

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 📈 Streamlit Dashboard

Check out the Streamlit [app](./app/) for workout analysis & performance management.

### Start Streamlit App

```bash
cd app/
streamlit run app.py
```

### References

1. [Power Zones by Strava](https://stories.strava.com/articles/feel-the-power-calculate-your-training-pacing-zones-know-what-they-feel-like)
2. [Power Zones by Pro Cycling Coaching](https://www.procyclingcoaching.com/resources/power-training-zones-for-cycling)
3. [Strava Guide: Features to Take Your Training to The Next Level](https://stories.strava.com/articles/strava-guide-features-to-take-your-training-to-the-next-level)
4. [TSS, IF, NP](https://www.trainerroad.com/blog/tss-if-and-workout-levels-3-metrics-to-help-you-understand-your-training-and-get-faster/)
5. [TSS by Peaksware](https://www.trainingpeaks.com/learn/articles/how-to-plan-your-season-with-training-stress-score/)
6. [CTL by Peaksware](https://www.trainingpeaks.com/learn/articles/applying-the-numbers-part-1-chronic-training-load/)
7. [A blog about CTL and ATL](https://ssp3nc3r.github.io/post/2020-05-08-calculating-training-load-in-cycling/)
8. [More indepth CTL and ATL analysis](https://konakorgi.com/2020/01/29/entry-5-rest-and-recovery-part-1-managing-fatigue/)
9. [A blog about CTL, ATL, and TSB in Chinese](https://zhuanlan.zhihu.com/p/389912897)

## Strava API

- [Strava API Developer Guide](https://developers.strava.com/docs/getting-started/)
- `We require authentication via OAuth 2.0 to request data about any athlete.` [Authentication](https://developers.strava.com/docs/authentication/)

### OAuth 2.0 with Strava

1. Redirect the user to the Strava authorization page with the following parameters:

   - `client_id`: Your Strava API client ID
   - `redirect_uri`: The URL to redirect to after authorization. Must be within the callback domain specified by the application. localhost and 127.0.0.1 are white-listed.
   - `response_type`: Set to "code"
   - `scope`: The permissions you want to request (e.g., "read,activity:read")
   - `approval_prompt=force`: (optional) Forces the user to approve each time

   Example:

   ```bash
   https://www.strava.com/oauth/authorize?client_id=YOUR_CLIENT_ID&response_type=code&redirect_uri=YOUR_REDIRECT_URI&approval_prompt=force&scope=read,activity:read
   ```

2. After user approval, Strava redirects the user back to your specified `redirect_uri` with an authorization code in the URL query string:

   ```bash
   https://yourapp.com/callback?code=AUTHORIZATION_CODE&scope=accepted_scopes
   ```

3. The backend exchanges the authorization code for tokens:

   - Make a POST request to the Strava token endpoint with the following parameters:
     - `client_id`: Your Strava API client ID
     - `client_secret`: Your Strava API client secret
     - `code`: The authorization code received in step 2
     - `grant_type`: Set to "authorization_code"

   Example:

   ```bash
   curl -X POST https://www.strava.com/oauth/token \
   -d "client_id=YOUR_CLIENT_ID" \
   -d "client_secret=YOUR_CLIENT_SECRET" \
   -d "code=AUTHORIZATION_CODE" \
   -d "grant_type=authorization_code"
   ```

4. Strava responds with an access token and a refresh token:

   Strava's response includes JSON containing:

   - `access_token` (short-lived)
   - `refresh_token` (used to obtain new access tokens)
   - User information (e.g., athlete ID).
