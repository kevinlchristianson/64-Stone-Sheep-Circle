# Crew chat setup

The Chat tab keeps its messages in Google Firebase (Firestore). The free Spark plan
covers a job crew many times over and never pauses. Until `chat-config.js` is filled
in, the tab says chat isn't switched on yet. This job gets its own Firebase project,
so its chat is separate from any other job's.

1. Go to https://console.firebase.google.com and **Create a project** (any name, e.g.
   `stone-sheep-chat`). Google Analytics is not needed.
2. **Build > Authentication > Get started > Sign-in method**: enable **Anonymous**.
3. **Build > Firestore Database > Create database**: pick a location near you, start in
   **production mode**.
4. In Firestore, open the **Rules** tab, replace everything with the contents of
   [`firestore.rules`](firestore.rules), and press **Publish**.
5. **Project settings** (gear icon) > **General** > **Your apps** > the web icon `</>`.
   Register an app (no Hosting needed). Copy the `firebaseConfig` object it shows.
6. In `chat-config.js`, replace `firebase: null,` with `firebase: { …the pasted object… },`
   then bump `VERSION` in `sw.js` and `build/build.py` so phones pick up the change.

Contractors open the Chat tab, enter their name and trade once, and post. Everyone with
the app sees every message; the tab shows an unread count. A question asked right after
picking something on a sheet or in the 3D model is tagged with it (e.g. "E-1 · R12").
