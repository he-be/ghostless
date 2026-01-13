using UnityEngine;
using UniVRM10;
using uOSC;

[RequireComponent(typeof(uOscServer))]
public class GhostlessReceiver : MonoBehaviour
{
    [Header("Target Avatar (VRM 1.0)")]
    public Vrm10Instance vrm10Instance;
    public Animator animator;

    [Header("Face Mesh (Required for Micro-Expressions)")]
    public SkinnedMeshRenderer faceMesh; // Assign the main face mesh here

    [Header("BlendShape Names (Raw Name)")]
    // Enter the exact name from SkinnedMeshRenderer's BlendShapes list
    public string blinkShape = "Fcl_EYE_Close"; 
    public string browsUpShape = "Fcl_BRW_Fun"; 
    public string mouthShape = "Fcl_MTH_Joy";   

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

    // Initial Rotations & Indices
    private Quaternion initHeadRot, initSpineRot, initChestRot;
    private int idxBlink = -1, idxBrows = -1, idxMouth = -1;
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
        }
    }

    void LateUpdate()
    {
        if (vrm10Instance == null) return;
        if (!initialized) { Initialize(); return; }

        // 1. Smooth Body Motion
        currentHeadYaw = Mathf.SmoothDamp(currentHeadYaw, tHeadYaw, ref velYaw, smoothTime);
        currentHeadPitch = Mathf.SmoothDamp(currentHeadPitch, tHeadPitch, ref velPitch, smoothTime);
        currentBodySway = Mathf.SmoothDamp(currentBodySway, tBodySway, ref velSway, smoothTime);
        currentBreath = Mathf.SmoothDamp(currentBreath, tBreath, ref velBreath, smoothTime);

        ApplyBodyMotion();
        ApplyFaceDirect();
    }
    
    void Initialize()
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
            
            // Look up indices
            if (faceMesh != null)
            {
                var mesh = faceMesh.sharedMesh;
                if (mesh != null)
                {
                    idxBlink = mesh.GetBlendShapeIndex(blinkShape);
                    idxBrows = mesh.GetBlendShapeIndex(browsUpShape);
                    idxMouth = mesh.GetBlendShapeIndex(mouthShape);
                    
                    if (idxBlink == -1) Debug.LogWarning($"BlendShape '{blinkShape}' not found!");
                    if (idxBrows == -1) Debug.LogWarning($"BlendShape '{browsUpShape}' not found!");
                    if (idxMouth == -1) Debug.LogWarning($"BlendShape '{mouthShape}' not found!");
                }
            }
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

    void ApplyFaceDirect()
    {
        if (faceMesh == null) return;

        // Apply raw weights (0-100)
        if (idxBlink != -1) faceMesh.SetBlendShapeWeight(idxBlink, tBlink * 100f);
        if (idxBrows != -1) faceMesh.SetBlendShapeWeight(idxBrows, tBrowsUp * 100f);
        if (idxMouth != -1) faceMesh.SetBlendShapeWeight(idxMouth, tMouth * 100f);
    }
}
