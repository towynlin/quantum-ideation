# The New Quantum Era

E97 / June 15, 2026 / 45:09
Quantum Drug Discovery and the Path to Advantage with Sabrina Maniscalco

## Why This Episode Matters


Sabrina Maniscalco is one of the few people in quantum who has lived the full arc: two decades of academic work on open quantum systems and non-Markovian noise at Palermo, Turku, Edinburgh, and Helsinki, followed by founding Algorithmiq with three of her former researchers after an early Qiskit Camp. That trajectory matters now because Algorithmiq just had a landmark stretch — sole winner of the $2M Wellcome Leap Q4Bio prize for a quantum-enabled cancer drug discovery workflow, an €18M Series B, a global HQ move to Milan, and its Tensor Network Error Mitigation (TEM) function landing in IBM's Qiskit Functions catalog.

If you're trying to make sense of where quantum software actually creates value before fault tolerance arrives — and what a credible "trajectory to advantage" looks like when paired with real clients in life sciences — this is a grounded, technically specific conversation with someone building it.

This episode is brought to you by Outshift, Cisco's incubation engine. The need for computational power is rapidly increasing in every sector. From drug discovery to material innovation to complex financial modeling, classical systems are reaching their absolute limits. It's time for a paradigm shift. The answer is a scalable quantum network, built on open standards and vendor-agnostic architecture. By uniting distributed quantum devices, you unlock limitless computational power.

- Why a background in open quantum systems and non-Markovian noise turned out to be unusually well-suited to running algorithms on noisy near-term hardware
- The actual science behind the Q4Bio winning workflow: simulating excited-state dynamics of a photosensitizer drug already in Phase II clinical trials, on up to 100 qubits
- How quantum-boosted DMRG works — and why it gives you a built-in benchmark against the best classical method via the bond dimension
- The tradeoff Sabrina would and wouldn't make between more qubits and lower noise, and why neutral atoms' slower sampling rates matter for chemistry
- Why even fault-tolerant algorithms like quantum phase estimation still depend on getting state initialization and measurement right
- Algorithmiq's two-product structure: the Digital Quantum Interface (hardware-agnostic infrastructure) and the life sciences application framework
- How methods built for chemistry are now opening doors into optimization and GenAI — and why that direction emerged from the work, not from a strategy deck
- What the move from Helsinki to Milan signals about the European quantum ecosystem and Algorithmiq's commercial scale-up
- How an active learning pipeline is already proposing novel drug variants for synthesis in Prof. Sherri McFarland's lab

## Resources & Links

Guest & Company

- Algorithmiq — The company Sabrina co-founded with Guillermo García-Pérez, Matteo Rossi, and Boris Sokolov; quantum software for life sciences and chemistry.
- Sabrina Maniscalco — University of Helsinki Research Portal — Publication record covering open quantum systems, non-Markovian dynamics, and quantum information.
- Sabrina Maniscalco — AI for Good Bio — Consolidated bio covering academic roles and advisory positions, including IQOQI Austria and CERN's Quantum Technology Initiative.

The Q4Bio Win

- Algorithmiq Wins $2M Wellcome Leap Q4Bio Prize — Company announcement detailing the photodynamic therapy workflow.
- Wellcome Leap — Q4Bio Prize Announcement — Funder's perspective on finalists and criteria.
- IBM Quantum Blog — Q4Bio Finalists — IBM's account of the workflow and quantum-classical integration.

Funding & HQ Move

- Tech.eu — Algorithmiq's €18M Series B and Milan move — Coverage of Italy's largest quantum VC round to date.
- Quantum Computing Report — Algorithmiq Relocates to Milan — Strategic context including the Q4Bio win and IBM partnership.
- EU-Startups coverage — Investor lineup and Italy's National Quantum Strategy framing.

Quantum Advantage & Tooling

- IBM Quantum Blog — The Dawn of Quantum Advantage — Includes Algorithmiq's TEM (Tensor Network Error Mitigation) function in the Qiskit Functions catalog.
- Algorithmiq & IBM Quantum Advantage Tracker — The heterogeneous materials experiment Algorithmiq and IBM put forward as a community benchmark.
- Silicon Republic interview with Sabrina — Useful prior context on her philosophy of using quantum to simulate quantum systems.

Key Quotes & Insights

- On the foundation of the company's approach: "We learned very early what we thought were the bottlenecks of quantum computers — what you really need to worry about if you want to implement computation at scale." A direct line from Qiskit Camp Vermont to Algorithmiq's product strategy.
- On Q4Bio, in Sabrina's words: "This molecule is already in Phase II clinical trial. So it's not hydrogen. It's a real molecule." A useful counter to the common critique that quantum chemistry demos still live in toy-model land.
- On quantum-boosted DMRG (insight): In the worst case, the method matches the best classical technique; in the better case, it outperforms it — and the bond dimension tells you which regime you're in. Built-in benchmarking against the classical baseline.
- On the hardware tradeoff: Asked whether she'd prefer 100 higher-fidelity qubits or 200 noisier ones, Sabrina's answer is "it depends" — and the explanation about why neutral atoms' lower sampling rates limit chemistry use cases is one of the more concrete things you'll hear on platform tradeoffs.
- On strategy (insight): New verticals at Algorithmiq are emerging from the work, not the other way around — methods built for chemistry are turning out to be useful for optimization and GenAI. A different theory of how a deep-tech company should expand.

Related Episodes

- Ep. 43 — Informationally complete measurement and dual-rail qubits with Guillermo García-Pérez and Sean Weinberg — Algorithmiq's CSO and co-founder on the measurement techniques that underpin much of the company's stack.
- Ep. 31 — The Utility of Quantum Computing for Chemistry with Jamie Garcia — IBM's perspective on near-term quantum chemistry, a natural companion to this conversation.
- Ep. 89 — Quantum Chemistry's Classical Limits with Garnet Chan — A skeptical, important counterweight on where classical methods still dominate chemistry.
- Ep. 86 — Quantum Advantage Achieved with Dominik Hangleiter — A theorist's careful look at what "quantum advantage" actually means.
- Ep. 39 — Innovative Near-Term Quantum Algorithms with Toby Cubitt — Another European quantum software founder on bridging current hardware and useful algorithms.

Exploring quantum technology, science & the future.

© 2026 the new quantum era, llc. All rights reserved.

## Transcript

Sebastian Hassinger (00:01.272)
Sabrina, hello. Thank you very much for joining me. I would love to get a bit of an introduction because I you've got a very unique background, even for people within quantum. So why we start with that?

Sabrina Maniscalco (00:17.31)
Hi, Sebastian, really nice to be here. And I'll tell you a bit more about all my history, okay, at least in quantum. So I started my career in Sicily, in Italy, first of all, as a PhD student, master and PhD student. But then after that, I started to work in quantum. I always worked in quantum technologies.

I'm in academia before a funding algorithmic and in places that are maybe unusual because i moved first to the bulgaria sofia then to south africa i was working in derb and then again to bulgaria then i arrived to finland. Then i got my first professor ship in edinburgh and then back to finland where i lived for many many years and now is we are speaking i'm in milan because i moved to italy after.

Sebastian Hassinger (00:43.342)
Mm-hmm.

Sabrina Maniscalco (01:07.046)
22 years abroad is really quite something. Yes, yes, I'm quite excited.

Sebastian Hassinger (01:09.454)
Wow. Did Italy welcome you back as a conquering hero? Good.

Sabrina Maniscalco (01:16.568)
Yeah, I think so. And I'm extremely happy to be there. So I, as I said, I worked a lot on a research field when I was really in university, in academia, that is technically known as open quantum system. This is basically a field where you study how the effects of noise of different types of noise.

Sebastian Hassinger (01:20.312)
That's great.

Sebastian Hassinger (01:34.477)
Hmm.

Sabrina Maniscalco (01:40.621)
I'll tell you the behavior of quantum systems also complex quantum systems like a quantum computer could be but it could be also another type of technologies they're important for quantum communication for quantum sensing so that was really the background of my research and then what happened is that when I became a professor I started to have an incredible group this was in Finland and I started to have the very first interaction with that.

Sebastian Hassinger (01:54.636)
Hmm.

Sabrina Maniscalco (02:09.392)
first quantum computers at that time, IBM put on the cloud. And now they were just celebrating these 10 years anniversary. And I remember that the very first Qiskit camp, I think it's where we met the first time. Or maybe shortly after, because the second one.

Sebastian Hassinger (02:18.626)
Yeah. Yeah.

Sebastian Hassinger (02:23.34)
Yes. Shortly after, wasn't actually, this is the KISS KIT camp in Europe, I think, yeah. I think the first one you your group were at was the European KISS KIT camp, right? you in Vermont. Okay, okay, so we probably did meet at TJ Watson on the way to Vermont. Yeah, yeah, yeah, yeah. In the barn.

Sabrina Maniscalco (02:36.034)
No, no, I was in Vermont, the very first one, yeah, the Vermont one. yes, but yeah, exactly. Yeah, it was in Vermont and it was in the barn. Exactly. And there was me and what then were the next three co-founders. So all the co-founders of Algorithmic, our small team, they were at that time researchers in my group. And I remember it was really fun. I remember the disco.

all the fun we had. But also I remember that I was perhaps I was probably the only professor. I mean, it was weird that there were a lot of super nice, young, very brilliant students. And I was challenging myself and saying, OK, let's see what we can do. But it was it was it was really nice because you see in this way, we learned very early what we thought were, you know, the key points. What I say, the bottlenecks actually of quantum computers. What do need really to

Sebastian Hassinger (03:13.582)
Hmm.

Sebastian Hassinger (03:27.192)
Mm.

Sebastian Hassinger (03:32.878)
Mmm.

Sabrina Maniscalco (03:35.718)
worry about if you want to implement at scale computation. that is a little bit. And then in 2020, we founded algorithmic with the Guillermo Garquilla Perez, Matteo Rossi and Boris Sokolov that were in the same hackathon. So it was really exciting.

Sebastian Hassinger (03:51.374)
Yeah. Right. Yeah.

It's interesting. mean, you said your studies were in open quantum systems. So the open part is open to the environment, right? It's interacting with, yes. Okay. So that's interesting contextual preparation for NISC machines because their main sort of handicap is that they're too open to the environment, right? Compared to a fault tolerant quantum computer, they're noisy.

Sabrina Maniscalco (04:02.438)
Mm-hmm.

Yes, exactly. That's correct.

Sabrina Maniscalco (04:12.302)
Yes, absolutely.

Sebastian Hassinger (04:24.654)
prone to decoherence or prone to noisy results. is that sort of that mentality of like you have to deal with the shortcomings of the hardware, is that sort of baked into the algorithmic approach to quantum software? Yeah.

Sabrina Maniscalco (04:41.422)
Yes, definitely it is. And our, let's say, background clearly helped us. But it's actually quite interesting and surprising how many other very fundamental, let's say, problems, if you want in quantum physics, like measurement problems and how to make measurements in quantum systems actually play a key role. And I have to say that it's interesting because obviously I had

Having a background, had a network of people and the co-founders obviously were researchers in this field. But it's interesting how very often people associate the research we do because we also do error mitigation, for example, with my background. While for me, it's very important also to say that actually from research point of view, I started to be CEO.

I mean, I'm really doing a different job. So actually all the research is thanks to the CSO of algorithmic gear. So, I mean, it's interesting how having a different perspective is really something that can be helpful both from the research side, but also certainly from the perspective of learning a new job, like being CEO. So in this sense, I really, I like, and it's important to be connected.

Sebastian Hassinger (05:34.136)
Yeah.

Sebastian Hassinger (05:53.218)
Hmm. Hmm.

Sabrina Maniscalco (05:59.294)
with the team because I can follow what they're doing. But I've actually stopped doing research since a while now.

Sebastian Hassinger (06:05.358)
Yeah, yeah, yeah. Very common. think that's the, you know, academic group leaders end up being more leaders than scientists in many cases. And certainly in the private sector, leadership is, it's very engrossing. To do the job right, can't really have it part-time, right?

Sabrina Maniscalco (06:21.708)
Yeah.

Sabrina Maniscalco (06:26.423)
No, exactly, exactly. While I kept for some time an affiliation at the University of Helsinki as a professor, now I actually completely resigned, so I'm not even a professor anymore.

Sebastian Hassinger (06:37.632)
Right. That's a very big shift. So error mitigation has been a big part of what algorithmic has been working on tensor error mitigation, for example. But I mean, do you see that as algorithmic's product, or is that sort of an enabling technology for what the product is meant to do?

Sabrina Maniscalco (07:04.205)
Yes, it's a very good question. We have two types of products. One is an infrastructure software that is called the Digital Quantum Interface. And it's actually an interface between quantum computers and classical machines like supercomputers or even AI. Now, this Digital Quantum Interface includes error mitigation strategies like our own tensor network error mitigation, but it also includes many other, if you want, methodologies or

Sebastian Hassinger (07:24.034)
Hmm.

Sabrina Maniscalco (07:32.195)
techniques that need to be then optimized and packaged really to be used off the shelf by clients and users, like for example, the measurement one. And then we have a second product that is a framework for simulations of, would say primarily chemistry, life sciences. This is an application software. And this is, for example, where we work for simulating, for example, molecules like

Sebastian Hassinger (07:33.336)
Mm-hmm. Mm-hmm.

Sabrina Maniscalco (08:01.816)
One of our major application has been in photodynamic therapy for cancer treatment and other similar ones.

Sebastian Hassinger (08:06.478)
Hmm.

That's really interesting. I mean, that's the work that was involved in the recent Q4Bio win, the Welcome Leap Challenge. So tell me about what was involved in that project. And congratulations on the win, Yeah.

Sabrina Maniscalco (08:15.971)
Yes.

Sabrina Maniscalco (08:20.525)
Yes, this was a step. Thank you. We were so excited about it also, but it was a tremendous amount of work that of course for us was really very much aligned with what we do. So in a way it was very natural to participate. this was the project we worked on was in collaboration with the Cleveland Clinic and IBM. So what we did was to really align on a true

end user need because in this case, the medical doctor and bioengineers in Cleveland Clinic had a problem related to the lack of easy simulation of a drug. It's called a photosensitizer specifically. It's a type of drug that is used to cure certain types of cancers. And it's very interesting because it does not have strong side effects. So differently from chemotherapy or radiotherapy that are very heavy.

photodynamic therapy, this photosensitizer is something that is only activated by light irradiation. So a patient ingests the drug, it's absorbed by the cells and only in the location where the cancer is, the light allows to activate the drug and therefore to attack the tumor cells and kill them. So what is interesting is that the way in which I'm telling you already understand that the key process

Sebastian Hassinger (09:39.726)
Hmm.

Sabrina Maniscalco (09:47.65)
is the interaction of the molecule, the drug and light, because this is what activates the molecule. And this is what you need to simulate very accurately and the corresponding dynamics then that is related to this molecular process. So this photo activation process is inherently quantum because we are talking about interaction of molecules. So electronic states of the molecules and light.

Sebastian Hassinger (09:57.71)
Hmm. Mm-hmm.

Sebastian Hassinger (10:08.75)
Mm-hmm.

Sebastian Hassinger (10:13.326)
With photons, yeah, yeah. Yeah.

Sabrina Maniscalco (10:14.233)
So with photons, exactly. So obviously there is need for using a quantum description because very often, especially in drug discovery, but also in chemistry, approximate method, chemical methods work very well. Well, in this case, there was need to use a quantum computer. There was an end user interested in this. So it has an important applications.

Sebastian Hassinger (10:21.707)
Right.

Sebastian Hassinger (10:37.944)
Mm-hmm.

Sabrina Maniscalco (10:38.007)
And you could also use, so that was the main point. We develop a whole very complex framework to make it doable really on real devices now, and then link it to the progress of the hardware so that we can increase the complexity of the simulations as the hardware scale, till reaching the point of fault tolerance, of course. But the pipeline we created, which is transferable, is not just for this photosensitizer.

Sebastian Hassinger (10:48.707)
Mm.

Sebastian Hassinger (10:54.391)
Right.

Sabrina Maniscalco (11:04.589)
And let me tell you, Sebastian, I'm excited to say this, but this molecule is already in phase two clinical trial. So it's not hydrogen. It's a real molecule. We collaborate with the inventor of the molecule and we are working, combining also machine learning or active learning in this case to explore the space of variants. So it's a very complex case. It's not a trivial case. And the fact that we have demonstrated already on hardware up to 100 qubits on MBM devices.

Sebastian Hassinger (11:11.31)
Now. Yeah, yeah, yeah.

Sebastian Hassinger (11:26.914)
Mm-hmm.

Sabrina Maniscalco (11:34.421)
simulations that has scalability, that is for which actually there is potential for quantum advantage. In some sense, according to certain parameters, we already see how we can outperform classical simulations because this is really because of the method developed is a quantum boosted MRG. The MRG is a classical technique that most sophisticated computational technique in this case for these types of problems.

Sebastian Hassinger (11:38.19)
Hmm.

Sebastian Hassinger (11:57.943)
Mm-hmm.

Sebastian Hassinger (12:01.356)
Yeah.

Sabrina Maniscalco (12:02.979)
and it is quantum boosted and we see how we can outperform it on hardware then combining it obviously with classical supercomputing.

Sebastian Hassinger (12:10.446)
Is the performance increase, is it down to the fact that your simulation is more accurate than the approximate classical method, at least as a starting point, and that the accuracy carries through to a better performance on the classical side? Is it sort of like a quantum seed, if you will, for the classical? Because that's a common pattern, I think, that's emerging, yeah.

Sabrina Maniscalco (12:22.262)
Yeah.

Sabrina Maniscalco (12:30.048)
Yes, exactly. It is exactly so because we have, as you know, especially for near term quantum computers, you want to use them really to minimize the usage of the quantum computer and only for what they are really necessary. So in this case, we use them just to input the state. So we just create a circuit which is as close as possible to the ground or excited states of these molecules.

And this is everything we do. And then we sample. But because this ground and excited states contain too much entanglement or correlations in this case to be simulated classically, then we have a boost because we can do it on a quantum computer. Then we sample, but we cannot do it classically precisely because there is a technical term for the technical audience. It's called a bond dimension. Every time you have a...

Sebastian Hassinger (13:08.856)
Mm-hmm.

Sabrina Maniscalco (13:24.654)
tensor network methods, which are methods like the MRG, the bond dimension quantifies really the amount of correlations. If you want also the simulability, the classical simulability, the bond dimension is too high, you cannot simulate it classically. And you need a quantum computer because quantum computers are really good at generating entanglement and correlations as the circuit becomes deeper and deeper.

Sebastian Hassinger (13:31.916)
Mm. Right. Right.

Sebastian Hassinger (13:48.142)
That's almost the touchstone for any definition of quantum advantage is the degree of correlation within the system you're trying to simulate, right? mean, that's sort of, that's why that 50 qubits that are fully entangled is kind of the benchmark or the rule of thumb of roughly, right? If everything is entangled at 50 qubits, that's sort of the limit of what we're able to simulate classically. And beyond that, it's just not classically simulatable.

Sabrina Maniscalco (13:59.022)
Absolutely.

Sabrina Maniscalco (14:15.236)
That's very true. What makes this method very exciting is that it's called the QBDMRG. But the interesting part is that you can have some sort of performance guarantee. So you are always sure that in the worst case, if the quantum computer is very noisy,

you will always be as good as the classical corresponding method. But if the quantum computer actually is not noisy or has some noise, but is still able to generate certain amount of entanglement, then you outperform the classical technique. And you have a parameter which is very, very well known, which is this bone dimension that allows you actually to verify which is the regime in which you are. So it's a nice, very nice benchmarking.

Sebastian Hassinger (14:48.866)
Mm-hmm.

Sebastian Hassinger (14:59.532)
Right.

Sabrina Maniscalco (15:05.07)
technique because it's inherently compared to the classical method, is the MRG. So it's nice. We like it.

Sebastian Hassinger (15:13.494)
I'm curious, like, yeah, that's fascinating. I'm curious, if you had your choice in terms of performance of this algorithm, would you rather, you said you ran it on 100 qubits on an IBM superconducting system, would you rather have 100 qubits with higher fidelity, lower gate noise, lower error rates, or 200 qubits with the same noise characteristics as the 100? In other words, noisy but

larger scale is that more valuable or just lowering the noise and the errors in the same scale?

Sabrina Maniscalco (15:49.507)
That's a super, super good question. And the answer is it depends. Obviously, it depends. It always depends. Because, of course, as you point out, there are many other factors which are very much platform dependent. So, for example, if you think in terms of neutral atom platforms, we have amazing progress done by many, many companies, many groups on neutral atoms. And there you would have certainly much better error.

Sebastian Hassinger (15:52.29)
Thank you. Of course.

course.

Sabrina Maniscalco (16:19.116)
let's say error rates, the fidelity is much higher. But the problem in that case is that they're much slower devices. And so therefore you cannot sample efficiently. Every time you do chemistry, mean, every time you do chemistry, if you really want to do chemistry and you want to calculate properties, you need very many samples because you have to reach high accuracy.

Sebastian Hassinger (16:27.213)
Mm-hmm.

Right.

Sebastian Hassinger (16:40.29)
Yeah. Right.

Sabrina Maniscalco (16:41.572)
So for doing chemistry, it's really hard to use lower devices because the number of samples is generally much lower. If you use superconducting qubits, you can do, I don't know, millions of measurements. If you use neutral atoms, you can do a thousand, 10,000. So it's a huge gap when it comes to the error associated to the simulations.

Sebastian Hassinger (16:44.974)
Mm, right. Yeah.

Sebastian Hassinger (16:57.356)
Yeah. Yeah.

Yeah.

Sebastian Hassinger (17:03.862)
Interesting, interesting. are there, can you foresee eventually, let's say there is slow qubits, but they're 100 % fault tolerant, would you be able to get the same results with fewer samples if you knew the results were accurate or is it just inherent in the algorithm itself that it's probabilistic and therefore needs to be sampled to get your data?

Sabrina Maniscalco (17:16.494)
Yes.

Sabrina Maniscalco (17:28.996)
In general, not just the algorithm, but in general for any measurement of properties of chemistry independently from our algorithms, you will need to do many samples. This is just because quantum mechanics is probabilistic. So you have to calculate expectation values of observables and therefore you have to gather statistics. That's, I mean, very, very, very basic and it's not depending on our algorithm. It depends on

Sebastian Hassinger (17:39.502)
Yeah.

Right.

Right.

Sabrina Maniscalco (17:56.374)
all the times in which you want to measure a property through an observable and in chemistry, this is the case because you want to calculate property. So that is in general. But then of course, there is yet another important part which is related to fault tolerant algorithms. And in this case, this important part is which plays a key role is how well you can generate the initial state. So, because again,

Sebastian Hassinger (18:04.204)
Yeah. Right.

Sebastian Hassinger (18:23.649)
Hmm.

Sabrina Maniscalco (18:24.289)
We are talking about a very complex, many, many multi qubits active spaces of these molecules. So representations, if you want, simplify the representation of the molecules. But of course, imagine that the space of possible states for a hundred qubits is tremendously large. I mean, we know that it's an exponential problem. if you have to, if you start from the wrong state or even from a state, which is random,

Sebastian Hassinger (18:42.776)
Mm-hmm.

Sabrina Maniscalco (18:51.009)
You will never, it doesn't matter if you use our algorithm or fault tolerant algorithms like phase estimation is the most common algorithm in fault tolerance for fault tolerant quantum chemistry simulation. mean, unfortunately, you really have to very clearly move towards a state generated on the quantum computer that has a significant overlap with the state you want eventually to simulate. Now this is a yet another

type of problems for which we have another part of algorithms. So you see it's a pipeline where you have, we have to initialize the quantum computer, then you have to create the circuit in the best possible manner. Then you have to measure, super important how you measure to reduce the errors, to use as little number of samples as possible. And then you have to post process, not really as noise mitigation, but with DMRG. So it's, and all of these things are important.

Sebastian Hassinger (19:25.421)
Mm-hmm.

Sabrina Maniscalco (19:49.048)
They all have their advantage of challenges as we move to different physical implementations or platforms. So neutral atoms versus, for example, superconducting qubits. And they are all different. In a way, different parts will continue to be useful in the full tolerant era. For example, the state initialization and the measurements, they will remain also for a full tolerant quantum computer. But then instead, we can use quantum phase estimation.

Sebastian Hassinger (20:11.95)
Of course. Yeah.

Sabrina Maniscalco (20:17.333)
instead of just sampling, for example.

Sebastian Hassinger (20:18.006)
Right. I see. That's interesting. And also, it occurs to me when your description of sort of testing the photosensitivity of that molecule, to what degree, I mean, it feels like with everything with quantum computing, there's some amount of the sort of the engineering problem where you just described the pipelining, how do you break the problem down in a way that's manageable by the hardware? How do you mitigate the

Sabrina Maniscalco (20:34.647)
Hmm.

Sebastian Hassinger (20:47.502)
Shortcomings of the hardware, but there's also it feels like the exploration is also Revealing more and more about quantum mechanics itself. I mean the right I mean that there's there's a generalized learning about the the foundations of how the universe works when you try to Tackle this type of problem

Sabrina Maniscalco (20:56.766)
Absolutely, yes.

Sabrina Maniscalco (21:07.063)
But this is exactly, I think for me, at least the most exciting part of this field, because it's a field that go all the way from really applications, industrial, even industrial application, we're starting to think about all these industrial applications, all the way down to very basic quantum physics knowledge and to what are still the open problems in quantum physics.

Of course, a lot of the research, of course, we have a large research team. We also have software engineers and product people, but we still have a large research team and many of them bottlenecks and the type of research they do is still very fundamental. Obviously, it's oriented towards innovation, so towards a product, towards a client that has a need.

But it's interesting because even the researchers and those who are more even mathematical physicists, they're super excited because they can still do fundamental research.

Sebastian Hassinger (22:05.046)
Right. Yeah, mean, it seems in that context that you as a scientist who's now a leader of a corporation that now has just raised more funds and has re-headquartered in Milan, you have the unique profile suited for managing that spectrum all the way from fundamental research to

product development and go to market and all of the usual things that a tech startup has to deal with. What sort of the, is there some model that you use in your mind to try to balance those two? The sort of the curiosity driven, open-ended versus the very market driven, you know, engineering.

Sabrina Maniscalco (22:33.483)
Okay.

Sabrina Maniscalco (22:49.695)
Of course, of course, this is the big challenge because especially at the beginning, now we are five years old, but especially at the beginning, we needed to, let's say, when we started to hire the R &D people, we needed to, in a way, let them understand that it's different ways of doing research, even if you have the opportunity of doing R &D. And it's incredibly interesting to see this shift, how collaborating with the more product software engineering, but even the

you know, more commercial people in the company, because of the culture that we have created, they started to change their mentality in a way that they really understand what is needed. And so they themselves ask questions in terms of their research or set OKRs in a different manner. So they have shifted their usual way of doing research.

maintaining the appeal and the interest and the excitement of curiosity driven research, but being very mindful of moving in the direction of what is needed for the company and for creating a product and being useful to a client, of course. It's been a process.

Sebastian Hassinger (24:05.538)
Hmm. Yeah, mean, yeah. Yeah. I mean, it seems like at least from observing from the outside, Algorothmic has been very smart about picking things like the Welcome Leap Challenge, for example, that are a real customer problem, real world problem with value. Obviously, when you're testing a cancer drug, it's very easy to imagine what the value is, but also economic value.

Sabrina Maniscalco (24:18.818)
Mm-hmm.

Mm-hmm.

Sabrina Maniscalco (24:29.28)
Yes. Yes.

Sebastian Hassinger (24:33.182)
If you're looking more broadly than just that one drug testing scenario, do you see, as I said, you just closed a new round, you're five years in as you said, do you see a continuation of the focus on life sciences or do you think algorithmic will address other verticals in the future?

Sabrina Maniscalco (24:54.846)
That's another super interesting question because actually what has happened are two things. The first thing is that we realized from the product, the digital quantum interface, which is more low level in the stack, this is across verticals. So for example, recently there was a, we have a partnership with Regetti where they are exploring it for financial applications, just because again, it's not life sciences. So we already see how some parts, some,

Sebastian Hassinger (25:09.496)
Mm.

Sebastian Hassinger (25:17.816)
Mm-hmm.

Sabrina Maniscalco (25:23.99)
products of the, or some parts of the product can be used for different verticals. But also what has happened is that while doing research on the life sciences and chemistry, we realized that some of the algorithms actually really that we have developed and then patented or filed for patent are really useful for different things. And so we are now opening up.

Sebastian Hassinger (25:28.056)
Right.

Sabrina Maniscalco (25:53.811)
two different, let's say, directions. One is more related to optimization and the other one is more related to GenAI and AI. but these are, it's interesting because they don't come from an initial decision, okay, we will be doing everything. They come from the other side of, we are doing what we are focusing initially, although we have, of course, the infrastructure software, which in any case we need to have for anything. And then we realize, wait a second,

This algorithm, this method actually is super important also for these other things. And then we start growing in that direction. This type of approaching for me makes much more sense than starting a startup. Okay, but this is only my opinion. There can be other ways that basically directly tackle very many different verticals.

Sebastian Hassinger (26:25.816)
Hmm. Yeah.

Sebastian Hassinger (26:36.942)
Of course.

Sabrina Maniscalco (26:42.166)
just because if you want to really operate at scale and do very complex demonstrations, and you need to do them, you need to do them because otherwise you don't learn what are the difficulties, then it's much harder because I mean, each of these different verticals have different or different categories of algorithms, like quantum simulations versus optimization algorithms versus machine learning. They have very different methodologies. They are not the same. So only the other way around.

Sebastian Hassinger (26:50.786)
Right. Right.

Sebastian Hassinger (27:08.846)
Mm-hmm.

Sabrina Maniscalco (27:10.956)
to me, at least for us, makes more sense because it comes from a realization, okay, we can apply now this to this other type of...

Sebastian Hassinger (27:14.178)
Yeah, yeah.

Sebastian Hassinger (27:20.246)
Right, right. So is it fair to say you sort of tackle a problem with, chemistry simulation, and in order to solve that problem, you had to come up with strategies for dealing with the non-Markovian open quantum systems kind of aspect of the hardware that you're dealing with. And then those tools that you build for that solution, you

Sabrina Maniscalco (27:27.201)
Yeah.

Sabrina Maniscalco (27:38.39)
I mean.

Sebastian Hassinger (27:46.722)
can apply to other solutions that's naturally adjacent because the need for dealing with the noise, dealing with the shortcomings of the hardware is very similar. And there things like state preparation and sampling, et cetera. There are commonalities across even very different algorithms at the top, essentially.

Sabrina Maniscalco (27:59.478)
Yes.

Sabrina Maniscalco (28:05.963)
Yes, absolutely. This is what has happened. also, I mean, there is also always some sort of, if you want, some unpredictability, right? Because this is a field which is just evolving. So at some point, you just realize that, a second, then this is something we can absolutely do and we can do better than many other methods or many other ways. you keep being open.

Sebastian Hassinger (28:17.058)
You

Very quickly.

Sabrina Maniscalco (28:33.826)
without obviously losing the focus, you need to have some focus, but you keep being open to the field, how it evolves, how things change quickly, how unpredictable results or direction can come up. And of course, that is, and clearly we also guided by the type of clients that we have and by their needs. Yeah.

Sebastian Hassinger (28:55.638)
Right, right, right. Yeah, I mean, I've used this example before, this analogy before, but I just find it so compelling. What you're describing sounds to me like a version of Stan Ulam at Princeton Institute for Advanced Studies working with von Neumann on that system was trying to come up with a method to use that system for neutron diffusion calculations and came up with the Monte Carlo algorithm.

Sabrina Maniscalco (29:13.228)
Okay.

Sebastian Hassinger (29:24.428)
And it wasn't until 30 years later that somebody looked at the Monte Carlo and thought, hmm, maybe I can optimize this portfolio with this. And it was a combination of, of not having the hardware capacity at the time in the late forties, early fifties, to do something of that scale, but also just sort of an imagination, like to see it through that lens in a very open ended. And it feels like what you're trying to do in algorithmic is, is sort of tighten that loop is discover those techniques that can get,

Sabrina Maniscalco (29:32.609)
Yeah.

Sabrina Maniscalco (29:44.758)
Absolutely. Yes.

Sebastian Hassinger (29:53.622)
results and then deliver those to demands in the market or open questions in the market.

Sabrina Maniscalco (30:00.354)
Absolutely. it's true that of course the tradition comes from life sciences and chemistry simulations because we have very, very, very strong team and obviously winning Q4Bio, I mean, with the competitors that we had and like all the major incredible startups and the universities and credit was incredible. It's it's an external validation, which tells that we are leading in this field. at the same time,

Sebastian Hassinger (30:15.616)
Yes.

Sebastian Hassinger (30:21.902)
Yeah.

Sabrina Maniscalco (30:25.337)
It's a very good example, the one you gave, but think also about NVIDIA, for example, that started as really developing the GPUs for video games and graphic cards. And then suddenly, realize, that's perfect actually for AI and for machine learning. So it's the users by using a device that you understand and developing methods for this that you understand actually.

Sebastian Hassinger (30:31.342)
Mm-hmm.

Sebastian Hassinger (30:37.774)
That's right.

Sebastian Hassinger (30:43.629)
Right.

Sabrina Maniscalco (30:54.313)
what could be the potential new users and you explore them and then you can find actually something that is even more disruptive than your original application. absolutely yes.

Sebastian Hassinger (31:03.288)
Right, right. Yeah, I mean, I'll say again that that seems to be, you you're uniquely qualified for that challenge because it's balancing that sort of curiosity driven scientific exploration with finding market opportunities and directing that energy into addressing the market. what like,

If you I mean it's difficult because of the the rate of innovation and as you said the variability of the landscape of the quantum Technologies, what do you sort of see as the next major milestones for for Alkali algorithmic if you look a year or two ahead?

Sabrina Maniscalco (31:42.387)
Yes, so we have actually a series of milestones. One of them is of course related to the applications now of the framework that we have developed for health care and life sciences to different types of problems. We are continuing of course the photodynamic therapy for cancer treatment. There is a lot to be done, but we started already now with precisely the same pipeline because it is transferable to apply these to antimicrobial resistance problems.

And this is super interesting, super important, another of the sustainability development challenges. So it's really, it's a very important aspect. And then we are using, we applying the simulation pipeline to study metabolism or problems related to penipel. So it's again, we are perfectioning and applying it to different potentially really groundbreaking.

problems together with the clients of relevance and end users of in Alkaline Sciences. But then at the same time, clearly our major goal following these fundraising is in increasing the business commercial and marketing operations. So this is where we are growing. We started to grow. We already started to hire because it makes sense now because the market is really becoming more and more mature.

So that's exactly what needs to be done. And the timing is right and it's excellent because we just closed the new round. So it makes a lot of sense. And finally, the other important goal is instead more related to, if you want to really optimizing some of these more fundamental type of methodologies, the digital quantum interface.

Sebastian Hassinger (33:10.402)
Yeah.

Sabrina Maniscalco (33:30.613)
to different hardware providers because we not only initially we worked a lot with IBM, we keep working there some very important partners. But for example, now we have also collaborations with Microsoft that is more related to the neutral atoms, so to magna and the new quantum computers that is being deployed in the Novo Nordisk Foundation. And there, there is a number of methodologies that are

Sebastian Hassinger (33:32.654)
Hmm.

Sebastian Hassinger (33:46.574)
Mm-hmm.

Sebastian Hassinger (33:57.005)
Right.

Sabrina Maniscalco (34:00.032)
really optimal for neutral atoms. So then we are starting collaborations with Ion, sorry, with the Treptions startups. again, demonstrating and optimizing the algorithms in order to guarantee that they are agnostic is really important. And this is something which again is more at the level of the, I would say really software infrastructure, the digital quantum interface.

Sebastian Hassinger (34:02.776)
Mm.

Sebastian Hassinger (34:27.542)
Mm-hmm, right.

Sabrina Maniscalco (34:28.417)
methods like measurements, methods and so on and so forth. And they can be applied to different verticals. And so this is what we are doing at the same time. And clearly there are metrics that are related to revenue, to adoption and so on and so forth as all startups. let's say the most important directions are these three that I just mentioned.

Sebastian Hassinger (34:43.222)
Of course.

Sebastian Hassinger (34:51.256)
Yeah, interesting. Well, and it's what I think is really exciting is, as you said very early on, that the method that you developed for the Q4Bio challenge will improve as, verifiably improve as the hardware improves. And we're on this path now to, you know, probably by 2030, there'll be a system that is fault tolerant at a scale that is not simulatable anymore.

Sabrina Maniscalco (35:15.925)
Yes.

Sebastian Hassinger (35:19.214)
And somebody working with you now can expect the algorithms and the pipelines and the frameworks that you're developing to just get better and better and better and start to develop or deliver value that's just not realizable by any other means because we've passed that simulation threshold.

Sabrina Maniscalco (35:35.016)
Exactly.

That's exactly the case. And it's important when you have clients to start delivering value now, but then link the methodologies, the algorithms to the progress of the quantum computer so that they see where the truly disruptive part is. But again, some parts of, for example, we have with Professor Sherry McFarland, is the inventor of this photosensitizer. We have also, she's a lab where she synthesizes new molecules.

Sebastian Hassinger (36:02.115)
Hmm.

Sabrina Maniscalco (36:07.285)
And what we are doing is that we have an active learning pipeline that already now is able to generate variants of these molecules that are new, novel. So it's really a benis show with a quantum computer would be an ab initio input of active learning pipelines that generate new molecules and can then be tested.

Sebastian Hassinger (36:16.94)
Hmm.

Sebastian Hassinger (36:22.776)
Yeah.

Sabrina Maniscalco (36:30.941)
in the lab of Professor McFarland. So we have already three new candidates that she will be synthesizing. this type of, if you want, methodologies where we already use something with what we have now and be adapted perfectionists as the devices improve are key to build and to create industrial value.

Sebastian Hassinger (36:58.488)
That's fantastic. Well, Sabrina, thank you so much for joining me. This has been a really, really interesting conversation and I've always been impressed with what you've been doing with algorithmic and I continue to be. I look forward to the future. So thank you very much.

Sabrina Maniscalco (37:01.364)
Enter.

Sabrina Maniscalco (37:07.767)
Thank you.

Amazing. Thank you. Thank you, Sebastian. Bye.

Sebastian Hassinger (37:15.35)
Okay, great.