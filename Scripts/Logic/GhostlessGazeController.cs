using UnityEngine;
using System.Collections;

namespace Ghostless
{
    [DefaultExecutionOrder(21000)]
    public class GhostlessGazeController : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private Animator _animator;
        [SerializeField] private SkinnedMeshRenderer _faceMesh;

        [Header("Gaze Settings")]
        [SerializeField] private bool _enableEyeWander = true;
        [SerializeField] private float _eyeWanderAmount = 2.0f; // Degrees
        [SerializeField] private float _eyeWanderSpeed = 0.3f;

        [Header("Blink Settings")]
        [SerializeField] private bool _enableBlinking = true;
        [SerializeField] private float _baseBlinkInterval = 3.0f;

        // Internal State
        private Quaternion _initLeftEyeRot;
        private Quaternion _initRightEyeRot;
        
        private int _blinkLIndex = -1;
        private int _blinkRIndex = -1;
        private float _currentBlinkWeight = 0f;
        private Coroutine _blinkCoroutine;

        // Gaze State
        private enum GazeState { Wander, Glance, Scan }
        private GazeState _gazeState = GazeState.Wander;
        private float _gazeStateTimer = 0f;
        
        // Saccade State
        private float _saccadeTimer = 0f;
        private Vector3 _targetGazePoint = Vector3.zero;
        private Vector3 _currentGaze = Vector3.zero;

        // External State
        private float _arousal = 0.5f;

        public void SetArousal(float arousal)
        {
            _arousal = arousal;
        }

        public void Initialize(Animator animator, SkinnedMeshRenderer faceMesh = null)
        {
            _animator = animator;
            _faceMesh = faceMesh;

            if (_animator)
            {
                var lEye = _animator.GetBoneTransform(HumanBodyBones.LeftEye);
                var rEye = _animator.GetBoneTransform(HumanBodyBones.RightEye);
                if (lEye) _initLeftEyeRot = lEye.localRotation;
                if (rEye) _initRightEyeRot = rEye.localRotation;
            }

            if (_faceMesh)
            {
                _blinkLIndex = _faceMesh.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close_L"); 
                if (_blinkLIndex == -1) _blinkLIndex = _faceMesh.sharedMesh.GetBlendShapeIndex("Blink_L");
                
                _blinkRIndex = _faceMesh.sharedMesh.GetBlendShapeIndex("Fcl_EYE_Close_R");
                if (_blinkRIndex == -1) _blinkRIndex = _faceMesh.sharedMesh.GetBlendShapeIndex("Blink_R");
            }

            if (_enableBlinking && _blinkCoroutine == null)
            {
                _blinkCoroutine = StartCoroutine(BlinkRoutine());
            }
        }

        public void ManualLateUpdate()
        {
            if (!_animator) return;
            UpdateEyeLook();
            UpdateBlink();
        }

        private void UpdateBlink()
        {
             if (_faceMesh != null && _enableBlinking)
             {
                 if (_blinkLIndex != -1) _faceMesh.SetBlendShapeWeight(_blinkLIndex, _currentBlinkWeight);
                 if (_blinkRIndex != -1) _faceMesh.SetBlendShapeWeight(_blinkRIndex, _currentBlinkWeight);
             }
        }

        private void UpdateEyeLook()
        {
            if (!_enableEyeWander) return;
            
            // 1. High-Level State Logic (Switching modes)
            _gazeStateTimer -= Time.deltaTime;
            if (_gazeStateTimer <= 0)
            {
                float r = Random.value;
                if (r < 0.7f) 
                {
                    _gazeState = GazeState.Wander;
                    _gazeStateTimer = Random.Range(3.0f, 8.0f); // Stay in wander longer
                }
                else if (r < 0.85f) 
                {
                    _gazeState = GazeState.Glance;
                    _gazeStateTimer = Random.Range(2.0f, 4.0f); // Tuned frequency
                }
                else 
                {
                    _gazeState = GazeState.Scan;
                    _gazeStateTimer = Random.Range(2.0f, 4.0f);
                }
                // Reset saccade on state change for immediate effect
                _saccadeTimer = 0;
            }

            // 2. Micro-Saccade Logic (Move - Stop - Move)
            _saccadeTimer -= Time.deltaTime;
            if (_saccadeTimer <= 0)
            {
                // Pick new Fixation Point
                if (_gazeState == GazeState.Wander)
                {
                     // Random point within range (Clamped 60% logic applied here in selection)
                     // Center bias: often near (0,0)
                     float rangeX = _eyeWanderAmount * 0.9f; // Yaw (reduced)
                     float rangeY = _eyeWanderAmount * 0.6f; // Pitch (Reduced 40%)
                     
                     float u = Random.value;
                     float wX = (u * u) * (Random.value > 0.5f ? 1 : -1) * rangeY; // Pitch
                     float wY = (Random.value - 0.5f) * 2.0f * rangeX; // Yaw

                     _targetGazePoint = new Vector3(wX, wY, 0);
                     _saccadeTimer = Random.Range(0.8f, 6.0f); // Reduced freq (4x duration)
                }
                else if (_gazeState == GazeState.Glance)
                {
                    // Look at specific target (Side Monitor)
                    // Add slight noise
                    float n = (Random.value - 0.5f) * 2.0f;
                    _targetGazePoint = new Vector3(5.0f + n, -15.0f + n, 0);
                    _saccadeTimer = Random.Range(2.0f, 4.0f); // Reduced freq (4x duration)
                }
                else if (_gazeState == GazeState.Scan)
                {
                    // Reading / Scanning: Small jumps horizontally
                    float currentY = _targetGazePoint.y;
                    
                    if (currentY < -5.0f) // End of line
                    {
                        // Return High (Left)
                        currentY = Random.Range(5.0f, 9.0f);
                        // Maybe change line (Pitch)
                        _targetGazePoint = new Vector3(Random.Range(-2f, 2f), currentY, 0);
                        _saccadeTimer = 0.8f; // Slowed return
                    }
                    else
                    {
                        // Jump Right
                        currentY -= Random.Range(2.0f, 4.0f); 
                        _targetGazePoint = new Vector3(_targetGazePoint.x + Random.Range(-0.5f,0.5f), currentY, 0);
                        _saccadeTimer = Random.Range(0.3f, 0.6f); // Slowed reading
                    }
                }
            }

            // 3. Move Eyes
            _currentGaze = Vector3.Lerp(_currentGaze, _targetGazePoint, Time.deltaTime * 25.0f);

            var lEye = _animator.GetBoneTransform(HumanBodyBones.LeftEye);
            var rEye = _animator.GetBoneTransform(HumanBodyBones.RightEye);
            
            // Clamp Outward Rotation (White Eye Prevention)
            float maxOutward = 8.0f; 
            float maxInward = 30.0f; 

            if (lEye) 
            {
                // Left Eye: +Y is Outward
                float clampedY = Mathf.Clamp(_currentGaze.y, -maxInward, maxOutward);
                lEye.localRotation = _initLeftEyeRot * Quaternion.Euler(_currentGaze.x, clampedY, 0);
            }
            if (rEye) 
            {
                // Right Eye: -Y is Outward
                float clampedY = Mathf.Clamp(_currentGaze.y, -maxOutward, maxInward);
                rEye.localRotation = _initRightEyeRot * Quaternion.Euler(_currentGaze.x, clampedY, 0);
            }
        }

        private IEnumerator BlinkRoutine()
        {
             while (true)
             {
                 if (_enableBlinking)
                 {
                     float duration = 0.08f;
                     for (float t = 0; t < duration; t += Time.deltaTime)
                     {
                         _currentBlinkWeight = (t / duration) * 100f;
                         yield return null;
                     }
                     _currentBlinkWeight = 100f;

                     yield return new WaitForSeconds(Random.Range(0.01f, 0.05f));

                     for (float t = 0; t < duration; t += Time.deltaTime)
                     {
                         _currentBlinkWeight = 100f - ((t / duration) * 100f);
                         yield return null;
                     }
                     _currentBlinkWeight = 0f;
                 }

                 if (Random.value < 0.2f) 
                 {
                     yield return new WaitForSeconds(0.1f);
                     continue; 
                 }

                 float baseWait = Random.Range(_baseBlinkInterval * 0.5f, _baseBlinkInterval * 1.5f);
                 float waitTime = baseWait / (1.0f + _arousal); 
                 yield return new WaitForSeconds(waitTime);
             }
        }
    }
}
