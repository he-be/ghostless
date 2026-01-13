using UnityEngine;
using UniVRM10;
using uOSC;

[RequireComponent(typeof(uOscServer))]
public class GhostlessReceiver : MonoBehaviour
{
    [Header("Target Avatar (VRM 1.0)")]
    public Vrm10Instance vrm10Instance;
    public Animator animator;

    [Header("Motion Settings")]
    public float maxHeadValues = 30.0f; 
    public float maxBodySway = 5.0f;    
    public float breathIntensity = 2.0f;

    // Received Targets
    private float targetHeadYaw = 0f;
    private float targetHeadPitch = 0f;
    private float targetBodySway = 0f;
    private float targetBreath = 0f;

    // Smoothed Values
    private float currentHeadYaw, currentHeadPitch, currentBodySway, currentBreath;
    public float smoothTime = 0.1f;
    private float velYaw, velPitch, velSway, velBreath;

    // Initial Rotations
    private Quaternion initHeadRot;
    private Quaternion initSpineRot;
    private Quaternion initChestRot;
    private bool initialized = false;

    private void Start()
    {
        var server = GetComponent<uOscServer>();
        if (server != null) server.onDataReceived.AddListener(OnDataReceived);
        
        // Initialize rotations after a short delay or in Update (VRM might load late)
    }

    void OnDataReceived(Message message)
    {
        if (message.values.Length == 0) return;
        var val = message.values[0];
        float fVal = 0f;
        if (val is float f) fVal = f;
        else if (val is int i) fVal = (float)i;
        else if (val is double d) fVal = (float)d;

        switch (message.address)
        {
            case "/avatar/parameters/Expression":
                if (val is int iVal) ApplyExpression(iVal);
                break;
            case "/avatar/parameters/Gesture":
                if (val is int iVal2) ApplyGesture(iVal2);
                break;
            case "/avatar/parameters/HeadYaw": targetHeadYaw = fVal; break;
            case "/avatar/parameters/HeadPitch": targetHeadPitch = fVal; break;
            case "/avatar/parameters/BodySway": targetBodySway = fVal; break;
            case "/avatar/parameters/Breath": targetBreath = fVal; break;
        }
    }

    void LateUpdate() // Use LateUpdate after Animation applied
    {
        if (vrm10Instance == null) return;
        
        // Ensure we grab initial rotations once
        if (!initialized)
        {
            InitializeBones();
            return;
        }

        // Smooth
        currentHeadYaw = Mathf.SmoothDamp(currentHeadYaw, targetHeadYaw, ref velYaw, smoothTime);
        currentHeadPitch = Mathf.SmoothDamp(currentHeadPitch, targetHeadPitch, ref velPitch, smoothTime);
        currentBodySway = Mathf.SmoothDamp(currentBodySway, targetBodySway, ref velSway, smoothTime);
        currentBreath = Mathf.SmoothDamp(currentBreath, targetBreath, ref velBreath, smoothTime);

        ApplyMotion();
    }
    
    void InitializeBones()
    {
        var anim = vrm10Instance.GetComponent<Animator>();
        if (anim == null) return;
        var head = anim.GetBoneTransform(HumanBodyBones.Head);
        var spine = anim.GetBoneTransform(HumanBodyBones.Spine);
        var chest = anim.GetBoneTransform(HumanBodyBones.Chest);
        
        if (head && spine && chest)
        {
            initHeadRot = head.localRotation;
            initSpineRot = spine.localRotation;
            initChestRot = chest.localRotation;
            initialized = true;
        }
    }

    void ApplyMotion()
    {
        var anim = vrm10Instance.GetComponent<Animator>();
        if (anim == null) return;

        var head = anim.GetBoneTransform(HumanBodyBones.Head);
        var spine = anim.GetBoneTransform(HumanBodyBones.Spine);
        var chest = anim.GetBoneTransform(HumanBodyBones.Chest);

        // Apply RELATIVE to Initial Rotation
        // NOTE: In LateUpdate, Animator might overwrite unless we re-apply or use layers.
        // For simple overwriting (VRM usually overrides), we set localRotation.
        
        if (head != null)
        {
             Quaternion offset = Quaternion.Euler(currentHeadPitch * maxHeadValues, currentHeadYaw * maxHeadValues, 0);
             head.localRotation = initHeadRot * offset;
        }

        if (spine != null)
        {
             Quaternion offset = Quaternion.Euler(0, 0, currentBodySway * maxBodySway);
             spine.localRotation = initSpineRot * offset;
        }

        if (chest != null)
        {
             Quaternion offset = Quaternion.Euler(currentBreath * breathIntensity, 0, 0);
             chest.localRotation = initChestRot * offset;
        }
    }

    void ApplyExpression(int expressionId)
    {
        if (vrm10Instance == null) return;
        ClearExpressions();
        ExpressionKey key = ExpressionKey.CreateFromPreset(ExpressionPreset.neutral);
        switch (expressionId)
        {
            case 1: key = ExpressionKey.CreateFromPreset(ExpressionPreset.happy); break;
            case 2: key = ExpressionKey.CreateFromPreset(ExpressionPreset.angry); break;
            case 3: key = ExpressionKey.CreateFromPreset(ExpressionPreset.sad); break;
            case 4: key = ExpressionKey.CreateFromPreset(ExpressionPreset.relaxed); break;
            default: key = ExpressionKey.CreateFromPreset(ExpressionPreset.neutral); break;
        }
        vrm10Instance.Runtime.Expression.SetWeight(key, 1.0f);
    }

    void ClearExpressions()
    {
        if (vrm10Instance == null) return;
        vrm10Instance.Runtime.Expression.SetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.happy), 0f);
        vrm10Instance.Runtime.Expression.SetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.angry), 0f);
        vrm10Instance.Runtime.Expression.SetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.sad), 0f);
        vrm10Instance.Runtime.Expression.SetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.relaxed), 0f);
        vrm10Instance.Runtime.Expression.SetWeight(ExpressionKey.CreateFromPreset(ExpressionPreset.neutral), 0f);
    }

    void ApplyGesture(int gestureId) { if (animator != null) animator.SetInteger("Gesture", gestureId); }
}
