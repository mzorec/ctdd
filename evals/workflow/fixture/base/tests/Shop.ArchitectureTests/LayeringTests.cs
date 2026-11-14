namespace Shop.ArchitectureTests;

public sealed class LayeringTests
{
    [Fact]
    public void Domain_Should_Not_Reference_Application()
    {
        Assert.Empty(Layers.Domain.ReferencesTo(Layers.Application));
    }

    /// <summary>
    /// A repository abstraction may return only a Domain type, a BCL type,
    /// or a type declared beside it in Abstractions.
    /// </summary>
    [Fact]
    public void RepositoryAbstractions_Should_Not_Return_Application_Types()
    {
        Assert.Empty(Layers.Abstractions.ReturnTypesFrom("Shop.Application.Features"));
    }
}
