using UnityEngine;
using uOSC;
using Ghostless;

namespace Ghostless.Network
{
    /// <summary>
    /// The "Ear" of the Actor.
    /// Listens for High-Level Intents from the Python Director via OSC.
    /// Translates OSC messages into calls to GhostlessAvatarController.
    /// </summary>
    [RequireComponent(typeof(uOscServer))]
    public class GhostlessOscInput : MonoBehaviour
    {
        [Header("Target Controller")]
        public GhostlessAvatarController avatarController;

        private uOscServer _server;

        private void Start()
        {
            _server = GetComponent<uOscServer>();
            if (_server != null)
            {
                _server.onDataReceived.AddListener(OnDataReceived);
            }
            
            if (avatarController == null)
            {
                avatarController = GetComponent<GhostlessAvatarController>();
                // Fallback attempt to find it nearby
                if (avatarController == null)
                    avatarController = FindObjectOfType<GhostlessAvatarController>();
            }
        }

        private void OnDataReceived(Message message)
        {
            if (avatarController == null) return;
            if (message.values == null || message.values.Length == 0) return;

            // Route based on Address
            // Protocol:
            // /ghostless/state/emotion (string or int ID)
            // /ghostless/state/arousal (float)
            // /ghostless/control/speech (int/bool - 1=Speaking, 0=Silent)

            switch (message.address)
            {
                case "/ghostless/state/emotion":
                    HandleEquation(message.values[0]);
                    break;
                case "/ghostless/state/arousal":
                    HandleArousal(message.values[0]);
                    break;
                case "/ghostless/control/speech":
                    HandleSpeech(message.values[0]);
                    break;
                // Keep legacy or debug hooks if needed, but aim for clean cut
            }
        }

        private void HandleEquation(object value)
        {
            if (value is string strVal)
            {
                avatarController.SetEmotion(strVal);
            }
            else if (value is int intVal)
            {
                // Simple numeric mapping if Python sends ints
                string[] emotions = { "neutral", "joy", "angry", "sorrow", "fun" };
                if (intVal >= 0 && intVal < emotions.Length)
                {
                    avatarController.SetEmotion(emotions[intVal]);
                }
            }
        }

        private void HandleArousal(object value)
        {
            float fVal = ExtractFloat(value);
            avatarController.SetArousal(fVal);
        }

        private void HandleSpeech(object value)
        {
            // Accept int (1/0), float (1.0/0.0), or bool (if uOSC supports it, usually it sends Int or Float)
            float fVal = ExtractFloat(value);
            bool isSpeaking = fVal > 0.5f;
            avatarController.SetSpeakingState(isSpeaking);
        }

        private float ExtractFloat(object val)
        {
            if (val is float f) return f;
            if (val is int i) return (float)i;
            if (val is double d) return (float)d;
            return 0f;
        }
    }
}
