using UnityEngine;
using UniVRM10;
using uOSC;

[RequireComponent(typeof(uOscServer))]
public class GhostlessReceiver : MonoBehaviour
{
    [Header("Target Avatar (VRM 1.0)")]
    public Vrm10Instance vrm10Instance;
    public Animator animator;

    [Header("Expression Key Names (Custom)")]
    // Enter the exact name of the Clip in your VRM
    public string blinkKey = "Blink";      // Standard: Blink
    public string browsUpKey = "BrowsUp";  // Custom: e.g., BrowInnerUp, Fcl_BRW_Up, Fun
    public string mouthKey = "MouthSmile"; // Custom: e.g., MouthSmile, Fcl_MTH_Smile, Joy

    [Header("Motion Settings")]
    public float maxHeadValues = 30.0f; 
    public float maxBodySway = 5.0f;    
    public float breathIntensity = 2.0f;

    // Smoothed Values
    private float currentHeadYaw, currentHeadPitch, currentBodySway, currentBreath;
    private float velYaw, velPitch, velSway, velBreath;
    public float smoothTime = 0.1f;
    
    // OSC Targets
    private float tHeadYaw, tHeadPitch, tBodySway, tBreath;
    private float tBlink, tBrowsUp, tMouth; 

    // Initial Rotations
    private Quaternion initHeadRot, initSpineRot, initChestRot;
    private bool initialized = false;

    private void Start()
    {
        var server = GetComponent<uOscServer>();
        if (server != null) server.onDataReceived.AddListener(OnDataReceived);
    }

    void OnDataReceived(Message message)
    {
        if (message.values.Length == 0) return;
        var val = message.values[0];
        float fVal = 0f;
        if (val is float f) fVal = f; else if (val is int i) fVal = (float)i; else if (val is double d) fVal = (float)d;

        switch (message.address)
        {
            // Body
            case "/avatar/parameters/HeadYaw": tHeadYaw = fVal; break;
            case "/avatar/parameters/HeadPitch": tHeadPitch = fVal; break;
            case "/avatar/parameters/BodySway": tBodySway = fVal; break;
            case "/avatar/parameters/Breath": tBreath = fVal; break;
            
            // Face
            case "/avatar/parameters/EyeBlink": tBlink = fVal; break;
            case "/avatar/parameters/BrowsUp": tBrowsUp = fVal; break;
            case "/avatar/parameters/MouthSmile": tMouth = fVal; break;

            // Legacy
            case "/avatar/parameters/Expression":
                if (val is int iVal) ApplyExpressionPreset(iVal);
                break;
        }
    }

    void LateUpdate()
    {
        if (vrm10Instance == null) return;
        if (!initialized) { InitializeBones(); return; }

        // 1. Smooth Body Motion
        currentHeadYaw = Mathf.SmoothDamp(currentHeadYaw, tHeadYaw, ref velYaw, smoothTime);
        currentHeadPitch = Mathf.SmoothDamp(currentHeadPitch, tHeadPitch, ref velPitch, smoothTime);
        currentBodySway = Mathf.SmoothDamp(currentBodySway, tBodySway, ref velSway, smoothTime);
        currentBreath = Mathf.SmoothDamp(currentBreath, tBreath, ref velBreath, smoothTime);

        ApplyBodyMotion();
        ApplyFace();
    }
    
    void InitializeBones()
    {
        var anim = vrm10Instance.GetComponent<Animator>();
        if (anim == null) return;
        var head = anim.GetBoneTransform(HumanBodyBones.Head);
        var spine = anim.GetBoneTransform(HumanBodyBones.Spine);
        var chest = anim.GetBoneTransform(HumanBodyBones.Chest);
        if (head && spine && chest) {
            initHeadRot = head.localRotation;
            initSpineRot = spine.localRotation;
            initChestRot = chest.localRotation;
            initialized = true;
        }
    }

    void ApplyBodyMotion()
    {
        var anim = vrm10Instance.GetComponent<Animator>();
        if (anim == null) return;
        var head = anim.GetBoneTransform(HumanBodyBones.Head);
        var spine = anim.GetBoneTransform(HumanBodyBones.Spine);
        var chest = anim.GetBoneTransform(HumanBodyBones.Chest);

        if (head) head.localRotation = initHeadRot * Quaternion.Euler(currentHeadPitch * maxHeadValues, currentHeadYaw * maxHeadValues, 0);
        if (spine) spine.localRotation = initSpineRot * Quaternion.Euler(0, 0, currentBodySway * maxBodySway);
        if (chest) chest.localRotation = initChestRot * Quaternion.Euler(currentBreath * breathIntensity, 0, 0);
    }

    void ApplyFace()
    {
        // Use CreateCustom to target specific Clip Names (case sensitive)
        // If the key doesn't exist, it usually does nothing or warns (check console).
        
        if (!string.IsNullOrEmpty(blinkKey))
            vrm10Instance.Runtime.Expression.SetWeight(ExpressionKey.CreateCustom(blinkKey), tBlink);

        if (!string.IsNullOrEmpty(browsUpKey))
            vrm10Instance.Runtime.Expression.SetWeight(ExpressionKey.CreateCustom(browsUpKey), tBrowsUp);

        if (!string.IsNullOrEmpty(mouthKey))
            vrm10Instance.Runtime.Expression.SetWeight(ExpressionKey.CreateCustom(mouthKey), tMouth);
    }

    void ApplyExpressionPreset(int id) 
    {
        // Legacy Support
    }
}
