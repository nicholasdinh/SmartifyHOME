from imutils import paths
import face_recognition
import pickle
import cv2
import os

def encode_faces(imageFolder):
    imagePaths = list(paths.list_images(imageFolder))
    knownEncodings = []
    knownNames = []

    for (i, imagePath) in enumerate(imagePaths):
        print("[INFO] processing image {}/{}".format(i + 1, len(imagePaths)))
        name = imagePath.split(os.path.sep)[-2]
        image = cv2.imread(imagePath)
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        boxes = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, boxes)
        for encoding in encodings:
            knownEncodings.append(encoding)
            knownNames.append(name)
    data = {"encodings": knownEncodings, "names": knownNames}
    return data

def encode_and_write_to_file(imageFolder):
    encodings = encode_faces(imageFolder)
    f = open("encodings.pickle", "wb")
    f.write(pickle.dumps(encodings))
    f.close()

if __name__ == "__main__":
    encode_and_write_to_file("./dataset")