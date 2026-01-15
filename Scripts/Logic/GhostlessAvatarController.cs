using UnityEngine;
using UniVRM10;
using System.Collections.Generic;

namespace Ghostless
{
    /// <summary>
    /// The "Actor" brain.
    /// Manages high-level emotion states and coordinates sub-behaviors (Gaze, Motion).
    /// </summary>
    [DefaultExecutionOrder(21000)] // Run AFTER VRM
    public class GhostlessAvatarController : MonoBehaviour
    {
        [Header("Target Avatar")]
        [SerializeField] private Vrm10Instance _vrmInstance;
        [SerializeField] private Animator _animator;

        [Header("Components")]
        [SerializeField] private GhostlessGazeController _gazeController;
        [SerializeField] private GhostlessMotionController _motionController;

        [Header("Debug")]
        [SerializeField] private bool _debugSpeechOverride = false;
        [SerializeField] private float _debugSpeechValue = 1.0f;

        [Header("State (ReadOnly)")]
        [SerializeField] private string _currentEmotion = "neutral";
        [SerializeField] private float _arousal = 0.5f; 
        [SerializeField] private bool _isSpeaking = false;

        // VRM 1.0 Standard Expression Keys
        private Dictionary<string, ExpressionKey> _emotionMap;

        private void Start()
        {
            if (_vrmInstance == null) _vrmInstance = GetComponent<Vrm10Instance>();
            if (_animator == null && _vrmInstance != null) _animator = _vrmInstance.GetComponent<Animator>();

            // Auto-create or find sub-components if missing
            if (!_gazeController) _gazeController = GetComponent<GhostlessGazeController>() ?? gameObject.AddComponent<GhostlessGazeController>();
            if (!_motionController) _motionController = GetComponent<GhostlessMotionController>() ?? gameObject.AddComponent<GhostlessMotionController>();

            InitializeExpressions();
            InitializeSubComponents();
        }

        private void InitializeSubComponents()
        {
            if (_animator == null) 
            {
                Debug.LogError("[Ghostless] Animator is null!");
                return;
            }

            // Find Face Mesh for Gaze Controller
            SkinnedMeshRenderer faceMesh = null;
            var smrs = GetComponentsInChildren<SkinnedMeshRenderer>();
            foreach(var smr in smrs)
            {
                if (smr.sharedMesh.blendShapeCount > 0)
                {
                    // Heuristic: check for Blink/Eye blendshapes
                    if (smr.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close_L") != -1 || 
                        smr.sharedMesh.GetBlendShapeIndex("Blink_L") != -1)
                    {
                        faceMesh = smr;
                        break;
                    }
                }
            }

            _gazeController.Initialize(_animator, faceMesh);
            _motionController.Initialize(_animator, _vrmInstance);
            
            // Sync initial state
            _gazeController.SetArousal(_arousal);
            _motionController.SetArousal(_arousal);
            _motionController.SetSpeakingState(_isSpeaking);
        }
        
        private void InitializeExpressions()
        {
            _emotionMap = new Dictionary<string, ExpressionKey>
            {
                { "neutral", ExpressionKey.CreateFromPreset(ExpressionPreset.neutral) },
                { "joy", ExpressionKey.CreateFromPreset(ExpressionPreset.happy) },
                { "angry", ExpressionKey.CreateFromPreset(ExpressionPreset.angry) },
                { "sorrow", ExpressionKey.CreateFromPreset(ExpressionPreset.sad) },
                { "fun", ExpressionKey.CreateFromPreset(ExpressionPreset.relaxed) }, 
                { "surprise", ExpressionKey.CreateFromPreset(ExpressionPreset.surprised) }
            };
        }

        // Use LateUpdate to override VRM animations
        private void LateUpdate()
        {
            if (_gazeController) _gazeController.ManualLateUpdate();
            if (_motionController) _motionController.ManualLateUpdate();
        }

        private void Update()
        {
            // Propagate Debug State in real-time (inspector edits)
            if (_motionController)
            {
                _motionController.SetDebugSpeech(_debugSpeechOverride, _debugSpeechValue);
            }
        }

        // --- Public / Director API ---

        public void SetEmotion(string emotionName)
        {
            if (_currentEmotion == emotionName) return;
            
            if (_emotionMap.ContainsKey(emotionName))
            {
                _currentEmotion = emotionName;
                ApplyEmotionToVRM(_emotionMap[emotionName]);
            }
            else
            {
                Debug.LogWarning($"[Ghostless] Unknown emotion: {emotionName}");
            }
        }

        private void ApplyEmotionToVRM(ExpressionKey key)
        {
            if (_vrmInstance == null || _vrmInstance.Runtime == null) return;
            
             _vrmInstance.Runtime.Expression.SetWeight(key, 1.0f);
             foreach(var kv in _emotionMap)
             {
                 if (!kv.Value.Equals(key))
                 {
                     _vrmInstance.Runtime.Expression.SetWeight(kv.Value, 0f);
                 }
             }
        }

        public void SetArousal(float value)
        {
            _arousal = Mathf.Clamp01(value);
            if (_gazeController) _gazeController.SetArousal(_arousal);
            if (_motionController) _motionController.SetArousal(_arousal);
        }

        public void SetSpeakingState(bool isSpeaking)
        {
            _isSpeaking = isSpeaking;
            if (_motionController) _motionController.SetSpeakingState(_isSpeaking);
        }
    }
}
