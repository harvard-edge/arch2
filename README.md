# Architecture 2.0: Designing the Loops that Design the Chips

[![Read the Book](https://img.shields.io/badge/Read_the_Book-Hosted_on_GitHub_Pages-blue?style=for-the-badge)](https://arch2.mlsysbook.ai)
[![Join the Discord](https://img.shields.io/badge/Discord-Join_the_Community-7289da?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/your-invite-link)
[![Hugging Face](https://img.shields.io/badge/%F0%9F%A4%97_Hugging_Face-Organization-FFD21E?style=for-the-badge)](https://huggingface.co/architecture20)

Welcome to the central repository for **Architecture 2.0**, a movement toward fully agentic, AI-driven design loops in computer architecture.

This repository serves two primary purposes:
1. **The Book Source Code:** It hosts the open-source Quarto markdown files for the work-in-progress synthesis lecture, *Architecture 2.0*. 
2. **The Living Catalog:** It is a community-driven registry of the tools, surrogates, and design loops that are making Architecture 2.0 a reality.

## 📖 The Book
Computer architecture is facing an existential crisis: we are trying to design trillion-transistor, hyperscale AI systems using manual, human-speed design loops. *Architecture 2.0* proposes a radical shift: instead of using AI merely to generate code, architects must design explicit, verifiable *loops* in which AI agents can safely operate.

You can read the latest compiled web version of the book here: [Read Architecture 2.0](https://arch2.mlsysbook.ai)

## 🛠 The Living Catalog (Community Submissions)
The ecosystem of AI tools for hardware design is moving faster than any static book can capture. 

We maintain a living catalog of Architecture 2.0 tools in the [**Awesome Architecture 2.0 List**](AWESOME.md). If you have built an open-source tool, proxy model, simulator environment, or agentic workflow, **we want to feature it!**

👉 **[Submit your tool to the catalog here](https://github.com/harvard-edge/architecture20/issues/new/choose)** using our automated Issue Template.

## 🌐 The Community
Architecture 2.0 requires a village. We are building a community of hardware purists, ML systems researchers, and EDA developers.
* **Join the Discord:** Come chat with us, share your loops, and discuss the book! (Link coming soon)
* **Hugging Face Hub:** While this GitHub repo hosts the book and tool registry, we encourage researchers to host their pre-trained architecture surrogates, proxy models, and datasets on the [Hugging Face Hub](https://huggingface.co/architecture20).

## Building the Book Locally
If you want to compile the book yourself (to output PDF, HTML, or EPUB), you will need to install [Quarto](https://quarto.org/).

```bash
# Clone the repository
git clone https://github.com/harvard-edge/architecture20.git
cd architecture20/synthesis/book

# Render the HTML version
quarto render --to html

# Render the PDF version (requires LaTeX)
quarto render --to pdf
```

## Contributing
See our [Contributing Guide](CONTRIBUTING.md) for details on how to submit typos, propose new content, or add your tool to the catalog.
