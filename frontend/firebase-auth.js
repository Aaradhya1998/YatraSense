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
    const userRef = doc(db, "users", user.uid);
    const existingUserDoc = await getDoc(userRef);
    const existingProfile = existingUserDoc.exists() ? existingUserDoc.data() : {};

    // Save user profile to Firestore
    await setDoc(userRef, {
      name: user.displayName,
      email: user.email,
      photo: user.photoURL,
      phone: existingProfile.phone || "",
      emergencyContact: existingProfile.emergencyContact || "",
      lastSeen: new Date().toISOString()
    }, { merge: true });

    currentUser = {
      uid: user.uid,
      name: user.displayName,
      email: user.email,
      photo: user.photoURL,
      phone: existingProfile.phone || "",
      emergencyContact: existingProfile.emergencyContact || ""
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

    // Show profile setup if phone missing.
    if (!currentUser.phone) {
      setTimeout(() => {
        if (document.getElementById("profile-overlay")) return;
        showProfileSetup(currentUser);
      }, 1500);
    }
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

function showProfileSetup(user) {
  // Create overlay
  const overlay = document.createElement("div");
  overlay.id = "profile-overlay";
  overlay.style.cssText = `
    position: fixed; top: 0; left: 0;
    width: 100vw; height: 100vh;
    background: rgba(28,16,7,0.85);
    z-index: 9999;
    display: flex; align-items: center; justify-content: center;
  `;

  overlay.innerHTML = `
    <div style="
      background: #FDF7EC;
      border-radius: 20px;
      padding: 28px 24px;
      width: 320px;
      max-width: 90vw;
      font-family: 'Nunito', sans-serif;
    ">
      <div style="display:flex; align-items:center; gap:12px; margin-bottom:20px;">
        <img src="${user.photo}" style="width:48px;height:48px;border-radius:50%;">
        <div>
          <div style="font-weight:800; font-size:16px; color:#1C1007;">
            Welcome, ${user.name.split(" ")[0]}!
          </div>
          <div style="font-size:12px; color:#7A6652;">
            Complete your profile for SOS safety
          </div>
        </div>
      </div>

      <div style="margin-bottom:14px;">
        <label style="font-size:12px; font-weight:700; color:#7A6652; display:block; margin-bottom:6px;">
          YOUR PHONE NUMBER
        </label>
        <input
          id="profile-phone"
          type="tel"
          placeholder="+91 98765 43210"
          style="
            width: 100%; padding: 12px 16px;
            border: 1.5px solid #A0522D;
            border-radius: 12px; font-size: 15px;
            font-family: 'DM Sans', sans-serif;
            background: white; color: #1C1007;
            box-sizing: border-box;
          "
        >
      </div>

      <div style="margin-bottom:20px;">
        <label style="font-size:12px; font-weight:700; color:#7A6652; display:block; margin-bottom:6px;">
          EMERGENCY CONTACT NAME & NUMBER
        </label>
        <input
          id="profile-emergency"
          type="text"
          placeholder="Mom - +91 98765 43210"
          style="
            width: 100%; padding: 12px 16px;
            border: 1.5px solid #A0522D;
            border-radius: 12px; font-size: 15px;
            font-family: 'DM Sans', sans-serif;
            background: white; color: #1C1007;
            box-sizing: border-box;
          "
        >
      </div>

      <div style="font-size:11px; color:#7A6652; margin-bottom:16px; line-height:1.5;">
        This information is only used if you trigger an emergency SOS.
        It will be sent to site authorities to help locate you.
      </div>

      <button
        id="profile-save-btn"
        style="
          width:100%; background:#E8621A; color:white;
          border:none; border-radius:24px; padding:14px;
          font-family:'Nunito'; font-weight:700; font-size:16px;
          cursor:pointer; margin-bottom:10px;
        "
      >Save Profile</button>

      <button
        id="profile-skip-btn"
        style="
          width:100%; background:none; color:#7A6652;
          border:1px solid #A0522D; border-radius:24px; padding:10px;
          font-family:'Nunito'; font-weight:600; font-size:14px;
          cursor:pointer;
        "
      >Skip for now</button>
    </div>
  `;

  document.body.appendChild(overlay);

  // Save button handler
  document.getElementById("profile-save-btn").addEventListener("click", async () => {
    const phone = document.getElementById("profile-phone").value.trim();
    const emergency = document.getElementById("profile-emergency").value.trim();

    if (!phone) {
      document.getElementById("profile-phone").style.borderColor = "#C0392B";
      return;
    }

    const btn = document.getElementById("profile-save-btn");
    btn.textContent = "Saving...";
    btn.disabled = true;

    await updateUserProfile(phone, emergency);
    overlay.remove();

    if (window.showToast) {
      window.showToast("Profile saved - SOS is ready");
    }
  });

  // Skip button handler
  document.getElementById("profile-skip-btn").addEventListener("click", () => {
    overlay.remove();
  });
}

export {
  signInWithGoogle,
  signOutUser,
  getCurrentUser,
  updateUserProfile,
  saveSosToFirestore,
  showProfileSetup
};
