# Distributed Image Processing

This demonstrates what is needed to be covered.

## Github Repo's

Currenty there are 3 repos:

- [Distributed Frontend](https://github.com/MazenTayseer/Distributed-Frontend): Contains the frontend
- [Distributed Backend](https://github.com/MazenTayseer/Distributed-Backend): Contains the server code
- [Distributed nodes](https://github.com/MazenTayseer/distributed-nodes): Contains the code to the machine nodes

## How to run

The website is hosted [here](https://distributed-frontend.vercel.app/), it will run fine as long as the machines are working!

To run locally, clone the frontend repo and run

```bash
npm install
```

To install necessary node modules

```bash
npm run dev
```

Server must be ran on the virtual machine, as it is in the same private network as other VMS.

## Technologies Used

- next.js: Frontend development
- flask: server
- mpi4py: distributed computing
- paramiko: ssh connections
- opencv: image proccessing tasks
- VGG-16: Classification Model
- ESRGAN: Image Enhancement

## Video Link

[Video Link](https://drive.google.com/drive/folders/1aWjpm2nNKLTQCVEWURcE369rMEL77eIE?usp=sharing)
