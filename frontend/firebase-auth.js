// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyC7PvCJrvZigZn25ww6KIcihnhiwnkj-y4",
  authDomain: "yatrasense.firebaseapp.com",
  projectId: "yatrasense",
  storageBucket: "yatrasense.firebasestorage.app",
  messagingSenderId: "1011809955018",
  appId: "1:1011809955018:web:a3b8a5a3f902489beb5833"
};

// Import Firebase from CDN (no build tools needed)
import { initializeApp } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-app.js";
import { getAuth, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-auth.js";
import { getFirestore, doc, setDoc, getDoc } from "https://www.gstatic.com/firebasejs/10.7.0/firebase-firestore.js";

const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);
const provider = new GoogleAuthProvider();

// Current user state
let currentUser = null;

// Sign in with Google
async function signInWithGoogle() {
  try {
    const result = await signInWithPopup(auth, provider);
    const user = result.user;

    // Save user profile to Firestore
    await setDoc(doc(db, "users", user.uid), {
      name: user.displayName,
      email: user.email,
      photo: user.photoURL,
      phone: "",
      emergencyContact: "",
      lastSeen: new Date().toISOString()
    }, { merge: true });

    currentUser = {
      uid: user.uid,
      name: user.displayName,
      email: user.email,
      photo: user.photoURL
    };

    return currentUser;
  } catch (err) {
    console.error("Sign in failed:", err);
    return null;
  }
}

// Sign out
async function signOutUser() {
  await signOut(auth);
  currentUser = null;
}

// Get current user
function getCurrentUser() {
  return currentUser;
}

// Update user profile (phone + emergency contact)
async function updateUserProfile(phone, emergencyContact) {
  if (!currentUser) return false;
  await setDoc(doc(db, "users", currentUser.uid), {
    phone,
    emergencyContact,
    updatedAt: new Date().toISOString()
  }, { merge: true });
  currentUser.phone = phone;
  currentUser.emergencyContact = emergencyContact;
  return true;
}

// Save SOS to Firestore with user identity
async function saveSosToFirestore(lat, lng, message) {
  console.log("saveSosToFirestore called with:", lat, lng, message);
  const user = getCurrentUser();
  console.log("User for SOS:", user);
  const sosData = {
    message,
    timestamp: new Date().toISOString(),
    location: { lat, lng },
    googleMapsLink: `https://maps.google.com/?q=${lat},${lng}`,
    user: user ? {
      uid: user.uid,
      name: user.name,
      email: user.email,
      phone: user.phone || "Not provided",
      emergencyContact: user.emergencyContact || "Not provided"
    } : { name: "Anonymous", phone: "Unknown" }
  };

  // Save to Firestore
  try {
    await setDoc(doc(db, "sos_alerts", `sos_${Date.now()}`), sosData);
    console.log("SOS saved to Firestore successfully");
  } catch (err) {
    console.error("Firestore save failed:", err);
  }
  return sosData;
}

// Listen to auth state changes
onAuthStateChanged(auth, async user => {
  if (user) {
    currentUser = {
      uid: user.uid,
      name: user.displayName,
      email: user.email,
      photo: user.photoURL
    };
    // Get additional profile data from Firestore
    const userDoc = await getDoc(doc(db, "users", user.uid));
    if (userDoc.exists()) {
      const data = userDoc.data();
      currentUser.phone = data.phone || "";
      currentUser.emergencyContact = data.emergencyContact || "";
    }
    updateAuthUI(true);
  } else {
    currentUser = null;
    updateAuthUI(false);
  }
});

// Update UI based on auth state
function updateAuthUI(isLoggedIn) {
  const loginBtn = document.getElementById("login-btn");
  const userPanel = document.getElementById("user-panel");
  const userName = document.getElementById("user-name");
  const userPhoto = document.getElementById("user-photo");

  if (!loginBtn) return;

  if (isLoggedIn && currentUser) {
    loginBtn.style.display = "none";
    if (userPanel) userPanel.style.display = "flex";
    if (userName) userName.textContent = currentUser.name;
    if (userPhoto) userPhoto.src = currentUser.photo;
  } else {
    loginBtn.style.display = "block";
    if (userPanel) userPanel.style.display = "none";
  }
}

export {
  signInWithGoogle,
  signOutUser,
  getCurrentUser,
  updateUserProfile,
  saveSosToFirestore
};
