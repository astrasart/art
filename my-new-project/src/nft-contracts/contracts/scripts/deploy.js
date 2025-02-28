const { ethers } = require("hardhat");

async function main() {
  const CyberpunkRobotNFT = await ethers.getContractFactory("CyberpunkRobotNFT");
  const nft = await CyberpunkRobotNFT.deploy();
  await nft.waitForDeployment();  // Use waitForDeployment() for Hardhat >= 2.9.0 with ethers 6.x
  console.log("CyberpunkRobotNFT deployed to:", await nft.getAddress());
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });