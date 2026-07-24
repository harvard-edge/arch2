import PyPDF2
import sys


def main():
    reader = PyPDF2.PdfReader(sys.argv[1])
    for i, page in enumerate(reader.pages):
        if "/Annots" in page:
            for annot in page["/Annots"]:
                obj = annot.get_object()
                if "/Contents" in obj:
                    print(f"Page {i+1}: {obj['/Contents']}")


if __name__ == "__main__":
    main()
