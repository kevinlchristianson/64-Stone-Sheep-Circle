// Crew chat settings. The chat stays switched off until `firebase` below is filled in.
// See CHAT-SETUP.md: create a free Firebase project for this job, turn on Anonymous
// sign-in and Firestore, then paste the web app's config object here. These values are
// not secrets; the rules in firestore.rules are what protect the data.
window.SSC_CHAT = {
  firebase: {
    apiKey: 'AIzaSyDk3cor3de9TaGbKzr-oA78Mb8YnFuvOmA',
    authDomain: 'stone-sheep-circle.firebaseapp.com',
    projectId: 'stone-sheep-circle',
    storageBucket: 'stone-sheep-circle.firebasestorage.app',
    messagingSenderId: '692619567008',
    appId: '1:692619567008:web:27a872349dd99751494ec5'
  },

  // One conversation per room. Change it to start a fresh thread.
  room: 'stone-sheep-crew',

  // Firebase JS SDK version loaded from gstatic.
  sdk: '12.18.0'
};
