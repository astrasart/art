// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Counters.sol";

contract CyberpunkRobotNFT is ERC721, Ownable {
    using Counters for Counters.Counter;
    Counters.Counter private _tokenIdCounter;

    // Base URI for IPFS metadata (your Pinata CID)
    string private baseURI = "ipfs://bafybeiei6e6swzzlxe6ivt4ux3subo2svxklwopelevrjfi54e6m2n3aae/";

    constructor() ERC721("CyberpunkRobotGIF", "CRGIF") {}

    function safeMint(address to) public onlyOwner {
        uint256 tokenId = _tokenIdCounter.current();
        require(tokenId < 100, "Max supply of 100 NFTs reached");
        _tokenIdCounter.increment();
        _safeMint(to, tokenId);
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        require(_exists(tokenId), "ERC721Metadata: URI query for nonexistent token");
        return string(abi.encodePacked(baseURI, "metadata.json"));  // Points to the metadata JSON file
    }

    function totalSupply() public view returns (uint256) {
        return _tokenIdCounter.current();
    }

    // Optional: Allow owner to update baseURI if Pinata CID changes
    function setBaseURI(string memory newBaseURI) public onlyOwner {
        baseURI = newBaseURI;
    }
}