"""
Export YOLO models to OpenVINO format for faster CPU inference on Intel.
Run once after installing dependencies: pip install ultralytics openvino
  

Exports in FP16 (half=True) for faster inference and lower memory with minimal
accuracy loss. For even more speed on edge/CPU, INT8 is possible via OpenVINO
quantization tools but requires calibration and may reduce accuracy.

Creates:
  - backend/yolo11n_openvino_model/  (person model)
  - <helmet_weights_dir>/<name>_openvino_model/  (helmet model, if .pt exists)


"""

import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_APP_DIR)


def _resolve_helmet_pt():
    """Same logic as server: find best.pt or helmet_detection_yolov11.pt."""
    candidates = []
    trained_best = os.path.join(_PROJECT_ROOT, "runs", "detect", "helmet_detection2", "weights", "best.pt")
    trained_named = os.path.join(_PROJECT_ROOT, "helmet_detection_yolov11.pt")
    if os.path.exists(trained_best):
        candidates.append((os.path.getmtime(trained_best), trained_best))
    if os.path.exists(trained_named):
        candidates.append((os.path.getmtime(trained_named), trained_named))
    runs_dir = os.path.join(_PROJECT_ROOT, "runs", "detect")
    if os.path.isdir(runs_dir):
        for name in os.listdir(runs_dir):
            best = os.path.join(runs_dir, name, "weights", "best.pt")
            if os.path.exists(best):
                candidates.append((os.path.getmtime(best), best))
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]
    return None


def main():
    from ultralytics import YOLO

    force = "--force" in sys.argv or "-f" in sys.argv

    # Export outputs go to cwd; run from project root so paths are predictable
    os.chdir(_PROJECT_ROOT)

    # --- Person model (COCO yolo11n) ---
    person_pt = "yolo11n.pt"
    out_person_dir = os.path.join(_APP_DIR, "yolo11n_openvino_model")
    if os.path.isdir(out_person_dir) and not force:
        print(f"[OpenVINO] Person model already exported: {out_person_dir}")
    else:
        if force and os.path.isdir(out_person_dir):
            import shutil
            try:
                shutil.rmtree(out_person_dir)
            except PermissionError:
                # Try _fp16 path (backend may have that loaded)
                out_person_dir = os.path.join(_APP_DIR, "yolo11n_openvino_model_fp16")
                if os.path.isdir(out_person_dir):
                    try:
                        shutil.rmtree(out_person_dir)
                    except PermissionError:
                        # Both locked (OneDrive, etc); export to fresh path
                        out_person_dir = os.path.join(_APP_DIR, "yolo11n_openvino_model_416")
                        if os.path.isdir(out_person_dir):
                            try:
                                shutil.rmtree(out_person_dir)
                            except PermissionError:
                                print("[OpenVINO] Cannot use fallback (in use):", out_person_dir)
                                return
                        print(f"[OpenVINO] Target in use; will export to: {out_person_dir}")
                else:
                    print(f"[OpenVINO] Target in use; will export to: {out_person_dir}")
        print(f"[OpenVINO] Exporting person model {person_pt} -> {out_person_dir}")
        try:
            model = YOLO(person_pt)
            # FP16 + imgsz=416: faster inference 
            model.export(format="openvino", half=True, imgsz=416)
            exported = os.path.join(_PROJECT_ROOT, "yolo11n_openvino_model")
            if os.path.isdir(exported):
                import shutil
                if os.path.isdir(out_person_dir) and os.path.abspath(exported) != os.path.abspath(out_person_dir):
                    try:
                        shutil.rmtree(out_person_dir)
                    except PermissionError:
                        pass
                if not os.path.isdir(out_person_dir):
                    shutil.move(exported, out_person_dir)
                    print(f"[OpenVINO] Moved to {out_person_dir}")
                else:
                    print(f"[OpenVINO] Person model at {exported} (target busy)")
            else:
                print(f"[OpenVINO] Person model exported to {exported}")
        except Exception as e:
            print(f"[OpenVINO] Person export failed: {e}")
            print("  Install openvino if needed: pip install openvino")

    # --- Helmet model ---
    helmet_pt = _resolve_helmet_pt()
    if not helmet_pt or not os.path.exists(helmet_pt):
        print("[OpenVINO] No helmet .pt found; skip helmet export.")
        return
    helmet_dir = os.path.dirname(helmet_pt)
    stem = os.path.splitext(os.path.basename(helmet_pt))[0]
    out_helmet_dir = os.path.join(helmet_dir, f"{stem}_openvino_model")
    if os.path.isdir(out_helmet_dir) and not force:
        print(f"[OpenVINO] Helmet model already exported: {out_helmet_dir}")
    else:
        if force and os.path.isdir(out_helmet_dir):
            import shutil
            try:
                shutil.rmtree(out_helmet_dir)
            except PermissionError:
                out_helmet_dir = os.path.join(helmet_dir, f"{stem}_openvino_model_fp16")
                if os.path.isdir(out_helmet_dir):
                    try:
                        shutil.rmtree(out_helmet_dir)
                    except PermissionError:
                        print("[OpenVINO] Cannot use fallback (in use):", out_helmet_dir)
                        return
                print(f"[OpenVINO] Target in use; will export to: {out_helmet_dir}")
        print(f"[OpenVINO] Exporting helmet model {helmet_pt} -> {out_helmet_dir}")
        try:
            model = YOLO(helmet_pt)
            # FP16: faster inference and less memory with minimal accuracy loss
            model.export(format="openvino", half=True)
            # Ultralytics creates {stem}_openvino_model in cwd (_PROJECT_ROOT)
            exported = os.path.join(_PROJECT_ROOT, f"{stem}_openvino_model")
            if os.path.isdir(exported) and os.path.abspath(exported) != os.path.abspath(out_helmet_dir):
                import shutil
                if os.path.isdir(out_helmet_dir):
                    try:
                        shutil.rmtree(out_helmet_dir)
                    except PermissionError:
                        pass
                if not os.path.isdir(out_helmet_dir):
                    shutil.move(exported, out_helmet_dir)
                    print(f"[OpenVINO] Helmet model exported to {out_helmet_dir}")
                else:
                    print(f"[OpenVINO] Helmet model at {exported} (target busy)")
            elif os.path.isdir(exported):
                print(f"[OpenVINO] Helmet model exported to {exported}")
            else:
                print(f"[OpenVINO] Helmet model exported to cwd: {stem}_openvino_model")
        except Exception as e:
            print(f"[OpenVINO] Helmet export failed: {e}")

    print("[OpenVINO] Done. Restart the backend to use OpenVINO inference.")


if __name__ == "__main__":
    sys.path.insert(0, _PROJECT_ROOT)
    main()
